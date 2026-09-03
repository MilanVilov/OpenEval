"""Evaluation runner — executes eval runs as background tasks."""

import asyncio
import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from src.comparers.base import BaseComparer
from src.db.models import Dataset, EvalConfig, EvalResult, EvalRun
from src.db.repositories import (
    ConfigRepository,
    DatasetRepository,
    ResultRepository,
    RunRepository,
    ScheduleRepository,
)
from src.db.session import get_session_context
from src.services import slack_notifier
from src.services.dataset_storage import iter_dataset_rows
from src.services.error_monitoring import report_exception
from src.services.eval_client import call_llm

logger = logging.getLogger(__name__)

MAX_ERROR_MESSAGE_LENGTH = 2000
RUN_HEARTBEAT_INTERVAL = timedelta(seconds=30)


@dataclass
class RunExecutionContext:
    """Dependencies and ORM objects needed to execute one run."""

    run_repo: RunRepository
    result_repo: ResultRepository
    run: EvalRun
    config: EvalConfig
    dataset: Dataset


@dataclass(frozen=True)
class GraderBundle:
    """Prepared grader instances and weight metadata."""

    comparers: list[tuple[str, BaseComparer]]
    weights: dict[str, float]


@dataclass
class _GraderStats:
    """Accumulate one grader's run statistics without retaining row results."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    unjudged: int = 0
    score_total: float = 0.0
    scored_count: int = 0

    def add(self, detail: dict) -> None:
        """Record one grader result."""
        self.total += 1
        if detail.get("passed") is True:
            self.passed += 1
        elif detail.get("passed") is False:
            self.failed += 1
        else:
            self.unjudged += 1
        score = detail.get("score")
        if isinstance(score, (int, float)):
            self.score_total += score
            self.scored_count += 1

    def build(self) -> dict:
        """Return the persisted summary shape for this grader."""
        judged = self.passed + self.failed
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "unjudged": self.unjudged,
            "judged": judged,
            "accuracy": self.passed / max(judged, 1),
            "avg_score": round(self.score_total / self.scored_count, 4)
            if self.scored_count
            else 0.0,
        }


@dataclass
class _RunSummary:
    """Accumulate run summary values while completed rows are persisted."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    unjudged: int = 0
    errors: int = 0
    latency_total: int = 0
    score_total: float = 0.0
    scored_count: int = 0
    input_token_total: int = 0
    input_token_count: int = 0
    output_token_total: int = 0
    output_token_count: int = 0
    graders: dict[str, _GraderStats] = field(default_factory=dict)

    def add(self, result: EvalResult) -> None:
        """Record one persisted result."""
        self.total += 1
        self.passed += result.passed is True
        self.failed += result.passed is False
        self.unjudged += result.passed is None and not result.error
        self.errors += bool(result.error)
        self.latency_total += result.latency_ms or 0
        self._add_score(result)
        self._add_token_usage(result)
        self._add_grader_details(result)

    def _add_score(self, result: EvalResult) -> None:
        if result.comparer_score is not None:
            self.score_total += result.comparer_score
            self.scored_count += 1

    def _add_token_usage(self, result: EvalResult) -> None:
        usage = result.token_usage or {}
        self._add_tokens(usage, "input_tokens")
        self._add_tokens(usage, "output_tokens")

    def _add_tokens(self, usage: dict, key: str) -> None:
        value = usage.get(key)
        if not isinstance(value, int):
            return
        if key == "input_tokens":
            self.input_token_total += value
            self.input_token_count += 1
        else:
            self.output_token_total += value
            self.output_token_count += 1

    def _add_grader_details(self, result: EvalResult) -> None:
        for name, detail in (result.comparer_details or {}).items():
            if isinstance(detail, dict):
                self.graders.setdefault(name, _GraderStats()).add(detail)

    def build(self) -> dict:
        """Return the persisted run summary."""
        judged = self.passed + self.failed
        return {
            "total": self.total,
            "judged": judged,
            "passed": self.passed,
            "failed": self.failed,
            "unjudged": self.unjudged,
            "errors": self.errors,
            "accuracy": self.passed / max(judged, 1),
            "avg_latency_ms": round(self.latency_total / max(self.total, 1)),
            "avg_score": round(self.score_total / max(self.scored_count, 1), 4),
            "avg_input_tokens": round(self.input_token_total / self.input_token_count)
            if self.input_token_count
            else 0,
            "avg_output_tokens": round(self.output_token_total / self.output_token_count)
            if self.output_token_count
            else 0,
            "grader_stats": {name: stats.build() for name, stats in self.graders.items()},
        }


def _run_tags(run_id: str, stage: str) -> dict[str, str]:
    """Return shared Sentry tags for one run exception."""
    return {"component": "eval_runner", "run_id": run_id, "stage": stage}


def _run_contexts(
    run_id: str,
    context: RunExecutionContext | None = None,
    *,
    extra_contexts: dict[str, dict[str, object]] | None = None,
) -> dict[str, dict[str, object]]:
    """Return shared Sentry contexts for one run exception."""
    contexts: dict[str, dict[str, object]] = {"run": {"id": run_id}}
    if context is not None:
        contexts["run"]["eval_config_id"] = context.run.eval_config_id
        contexts["run"]["dataset_id"] = context.run.dataset_id
        scheduled_by_id = _optional_string(getattr(context.run, "scheduled_by_id", None))
        if scheduled_by_id is not None:
            contexts["run"]["scheduled_by_id"] = scheduled_by_id
        contexts["config"] = {
            "model": context.config.model,
            "concurrency": context.config.concurrency,
            "tools": list(context.config.tools or []),
        }
        contexts["dataset"] = {"file_path": context.dataset.file_path}
    if extra_contexts:
        contexts.update(extra_contexts)
    return contexts


def _report_run_exception(
    exc: Exception,
    *,
    run_id: str,
    stage: str,
    context: RunExecutionContext | None = None,
    extra_contexts: dict[str, dict[str, object]] | None = None,
    extras: dict[str, object] | None = None,
) -> None:
    """Report one handled run exception to Sentry."""
    report_exception(
        exc,
        tags=_run_tags(run_id, stage),
        contexts=_run_contexts(run_id, context, extra_contexts=extra_contexts),
        extras=extras,
    )


def _row_context(result: EvalResult, row: dict) -> dict[str, object]:
    """Return lightweight row metadata for Sentry context."""
    return {
        "row_index": result.row_index,
        "row_keys": sorted(str(key) for key in row),
        "input_chars": len(result.input_data or ""),
        "expected_output_chars": len(result.expected_output or ""),
    }


def _optional_string(value: object) -> str | None:
    """Return one string only when ``value`` is a non-empty string."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


async def run_evaluation(run_id: str) -> None:
    """Execute an evaluation run in a background task."""
    try:
        await _run_evaluation(run_id)
    except Exception as exc:
        _report_run_exception(exc, run_id=run_id, stage="run_evaluation")
        logger.exception("Run %s crashed during execution", run_id)
        await _mark_run_failed(run_id, exc)


async def _run_evaluation(run_id: str) -> None:
    """Execute one run from row loading through summary generation."""
    async with get_session_context() as session:
        context = await _load_run_context(session, run_id)
        if context is None:
            return

        await _mark_run_started(context.run_repo, run_id)
        heartbeat_stop = asyncio.Event()
        heartbeat_task = asyncio.create_task(_heartbeat_until_stopped(run_id, heartbeat_stop))
        try:
            rows = await _read_rows(context)
            if rows is None:
                return

            await context.run_repo.update_status(
                run_id,
                status="running",
                heartbeat_at=datetime.now(UTC),
            )
            grader_bundle = _build_grader_bundle(context.config, context.run.flex_enabled)
            summary = await _process_rows(context, rows, grader_bundle)
            summary = await _mark_run_completed(context.run_repo, run_id, summary)
            logger.info("Run %s completed: %s", run_id, summary)
            slack_payload = await _gather_slack_payload(session, run_id)
        finally:
            await _stop_heartbeat(heartbeat_stop, heartbeat_task)

    await _send_slack_notification(run_id, slack_payload)


async def _load_run_context(session, run_id: str) -> RunExecutionContext | None:
    """Load the run and its required related objects."""
    run_repo = RunRepository(session)
    config_repo = ConfigRepository(session)
    dataset_repo = DatasetRepository(session)
    result_repo = ResultRepository(session)

    run = await run_repo.get_by_id(run_id)
    if run is None:
        logger.error("Run %s not found", run_id)
        return None

    config = await config_repo.get_by_id(run.eval_config_id)
    dataset = await dataset_repo.get_by_id_with_content(run.dataset_id)
    if config is None or dataset is None:
        await run_repo.update_status(
            run_id,
            status="failed",
            error_message="Run failed because the referenced config or dataset was not found.",
            completed_at=datetime.now(UTC),
            heartbeat_at=datetime.now(UTC),
        )
        return None

    return RunExecutionContext(
        run_repo=run_repo,
        result_repo=result_repo,
        run=run,
        config=config,
        dataset=dataset,
    )


async def _mark_run_started(run_repo: RunRepository, run_id: str) -> None:
    """Mark the run as running and record its start time."""
    now = datetime.now(UTC)
    await run_repo.update_status(
        run_id,
        status="running",
        error_message=None,
        started_at=now,
        heartbeat_at=now,
    )


async def _read_rows(
    context: RunExecutionContext,
) -> Iterator[dict] | None:
    """Open the dataset row iterator or mark the run failed."""
    try:
        return await iter_dataset_rows(context.dataset)
    except Exception as exc:
        _report_run_exception(exc, run_id=context.run.id, stage="read_dataset", context=context)
        logger.exception("Failed to read dataset for run %s", context.run.id)
        await context.run_repo.update_status(
            context.run.id,
            status="failed",
            error_message=_format_error_message("Failed to read dataset", exc),
            completed_at=datetime.now(UTC),
            heartbeat_at=datetime.now(UTC),
        )
        return None


def _build_grader_bundle(config: EvalConfig, flex_enabled: bool) -> GraderBundle:
    """Instantiate graders and collect their configured weights."""
    comparers: list[tuple[str, BaseComparer]] = []
    weights: dict[str, float] = {}
    for grader_def in config.graders or []:
        grader = _build_grader(grader_def, config.model, flex_enabled)
        comparers.append((grader.grader_name, grader))
        weights[grader.grader_name] = grader_def.get("weight", 1.0)
    return GraderBundle(comparers=comparers, weights=weights)


def _build_grader(
    grader_def: dict,
    default_model: str,
    flex_enabled: bool,
) -> BaseComparer:
    """Create one grader instance from a grader definition."""
    from src.comparers.custom_grader import CustomGraderComparer
    from src.comparers.json_field_match import JsonFieldMatchComparer
    from src.comparers.json_schema_match import JsonSchemaMatchComparer
    from src.comparers.python_grader import PythonGraderComparer
    from src.comparers.semantic_similarity import SemanticSimilarityComparer
    from src.comparers.string_check_grader import StringCheckGraderComparer

    grader_type = grader_def.get("type", "prompt")
    grader_cfg = {**grader_def}
    if grader_type == "string_check":
        return StringCheckGraderComparer(grader_cfg)
    if grader_type == "python":
        return PythonGraderComparer(grader_cfg)
    if grader_type == "semantic_similarity":
        return SemanticSimilarityComparer(grader_cfg)
    if grader_type == "json_schema":
        return JsonSchemaMatchComparer(grader_cfg)
    if grader_type == "json_field":
        return JsonFieldMatchComparer(grader_cfg)
    grader_cfg["model"] = grader_def.get("model") or default_model
    grader_cfg["flex_enabled"] = flex_enabled
    return CustomGraderComparer(grader_cfg)


async def _process_rows(
    context: RunExecutionContext,
    rows: Iterator[dict],
    grader_bundle: GraderBundle,
) -> dict:
    """Process rows with no more than the configured number in flight."""
    row_iterator = enumerate(rows)
    tasks = _start_row_tasks(row_iterator, context, grader_bundle)
    summary = _RunSummary()
    committed_count = 0

    try:
        while tasks:
            done, tasks = await asyncio.wait(
                tasks,
                timeout=RUN_HEARTBEAT_INTERVAL.total_seconds(),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                await _refresh_run_heartbeat(context, committed_count)
                continue

            for task in done:
                result = await task
                committed_count = await _flush_result_batch(
                    context,
                    result,
                    committed_count,
                    summary,
                )
                next_task = _next_row_task(row_iterator, context, grader_bundle)
                if next_task is not None:
                    tasks.add(next_task)
        return summary.build()
    except Exception:
        await _cancel_tasks(list(tasks))
        raise


def _start_row_tasks(
    rows: Iterator[tuple[int, dict]],
    context: RunExecutionContext,
    grader_bundle: GraderBundle,
) -> set[asyncio.Task[EvalResult]]:
    """Start up to the configured number of row tasks."""
    tasks: set[asyncio.Task[EvalResult]] = set()
    for _ in range(context.config.concurrency):
        task = _next_row_task(rows, context, grader_bundle)
        if task is None:
            break
        tasks.add(task)
    return tasks


def _next_row_task(
    rows: Iterator[tuple[int, dict]],
    context: RunExecutionContext,
    grader_bundle: GraderBundle,
) -> asyncio.Task[EvalResult] | None:
    """Create one task from the next dataset row when one is available."""
    try:
        index, row = next(rows)
    except StopIteration:
        return None
    return asyncio.create_task(_process_row(context.run.id, index, row, context, grader_bundle))


async def _process_row(
    run_id: str,
    index: int,
    row: dict,
    context: RunExecutionContext,
    grader_bundle: GraderBundle,
) -> EvalResult:
    """Process one row through the provider and grader pipeline."""
    result = _build_result(run_id, index, row)
    await _populate_row_result(result, row, context, grader_bundle)
    return result


async def _flush_result_batch(
    context: RunExecutionContext,
    result: EvalResult,
    committed_count: int,
    summary: _RunSummary,
) -> int:
    """Persist one result and advance progress only after commit succeeds."""
    await context.result_repo.upsert_batch([result])
    summary.add(result)
    committed_count += 1
    await _persist_run_progress(context, committed_count)
    return committed_count


async def _refresh_run_heartbeat(
    context: RunExecutionContext,
    committed_count: int,
) -> None:
    """Refresh the run heartbeat while waiting for slow in-flight rows."""
    await _persist_run_progress(context, committed_count)


async def _persist_run_progress(
    context: RunExecutionContext,
    committed_count: int,
) -> None:
    """Best-effort run progress persistence that never aborts the evaluation."""
    try:
        await context.run_repo.update_progress(
            context.run.id,
            progress=committed_count,
            heartbeat_at=datetime.now(UTC),
        )
    except Exception as exc:
        _report_run_exception(
            exc,
            run_id=context.run.id,
            stage="persist_progress",
            context=context,
            extra_contexts={"progress": {"committed_count": committed_count}},
        )
        logger.exception(
            "Progress update failed for run %s at %s rows",
            context.run.id,
            committed_count,
        )
        await _rollback_progress_update(context)


async def _rollback_progress_update(context: RunExecutionContext) -> None:
    """Clear the shared session after a non-fatal progress write failure."""
    try:
        await context.run_repo.rollback()
    except Exception as exc:
        _report_run_exception(
            exc,
            run_id=context.run.id,
            stage="rollback_progress",
            context=context,
        )
        logger.exception("Progress rollback failed for run %s", context.run.id)


async def _heartbeat_until_stopped(run_id: str, stop_event: asyncio.Event) -> None:
    """Refresh the run heartbeat until ``stop_event`` is set."""
    timeout_seconds = RUN_HEARTBEAT_INTERVAL.total_seconds()
    while True:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=timeout_seconds)
            return
        except TimeoutError:
            await _persist_heartbeat(run_id)


async def _persist_heartbeat(run_id: str) -> None:
    """Write a heartbeat using a short-lived session."""
    try:
        async with get_session_context() as session:
            await RunRepository(session).update_heartbeat(
                run_id,
                heartbeat_at=datetime.now(UTC),
            )
    except Exception as exc:
        _report_run_exception(exc, run_id=run_id, stage="persist_heartbeat")
        logger.exception("Heartbeat update failed for run %s", run_id)


async def _stop_heartbeat(
    stop_event: asyncio.Event,
    heartbeat_task: asyncio.Task[None],
) -> None:
    """Stop the heartbeat loop and wait for it to exit cleanly."""
    stop_event.set()
    await heartbeat_task


async def _mark_run_completed(
    run_repo: RunRepository,
    run_id: str,
    summary: dict,
) -> dict:
    """Store the final summary and mark the run completed."""
    now = datetime.now(UTC)
    await run_repo.update_status(
        run_id,
        status="finalizing",
        error_message=None,
        heartbeat_at=now,
    )
    await run_repo.set_summary(run_id, summary=summary)
    await run_repo.update_status(
        run_id,
        status="completed",
        error_message=None,
        completed_at=datetime.now(UTC),
        heartbeat_at=datetime.now(UTC),
    )
    return summary


def _build_result(run_id: str, index: int, row: dict) -> EvalResult:
    """Create the initial result object for one dataset row."""
    return EvalResult(
        eval_run_id=run_id,
        row_index=index,
        input_data=row.get("input", ""),
        expected_output=row.get("expected_output", ""),
    )


async def _populate_row_result(
    result: EvalResult,
    row: dict,
    context: RunExecutionContext,
    grader_bundle: GraderBundle,
) -> None:
    """Fill a result with model output and grader details."""
    try:
        llm_response = await call_llm(
            system_prompt=context.config.system_prompt,
            user_input=result.input_data,
            model=context.config.model,
            temperature=context.config.temperature,
            max_tokens=context.config.max_tokens,
            tools=context.config.tools,
            tool_options=context.config.tool_options,
            reasoning_config=context.config.reasoning_config,
            response_format=context.config.response_format,
            flex_enabled=context.run.flex_enabled,
        )
        result.actual_output = llm_response.text
        result.latency_ms = llm_response.latency_ms
        result.token_usage = llm_response.token_usage
        (
            result.comparer_score,
            result.passed,
            result.comparer_details,
        ) = await _apply_graders(
            context,
            grader_bundle,
            expected=result.expected_output,
            actual=llm_response.text,
            row_data=row,
            row_index=result.row_index,
        )
    except Exception as exc:
        result.passed = False
        result.error = str(exc)
        _report_run_exception(
            exc,
            run_id=context.run.id,
            stage="process_row",
            context=context,
            extra_contexts={"row": _row_context(result, row)},
        )
        logger.exception("Run %s row %s failed", context.run.id, result.row_index)


async def _apply_graders(
    context: RunExecutionContext,
    grader_bundle: GraderBundle,
    *,
    expected: str,
    actual: str,
    row_data: dict,
    row_index: int,
) -> tuple[float, bool | None, dict]:
    """Run all configured graders for one row and combine their outputs."""
    details: dict[str, dict] = {}
    weighted_scores: list[tuple[float, float]] = []
    weighted_passed: list[tuple[float, bool | None]] = []

    for name, comparer in grader_bundle.comparers:
        weight = grader_bundle.weights.get(name, 1.0)
        try:
            score, passed, grader_details = await comparer.compare(
                expected=expected,
                actual=actual,
                row_data=row_data,
            )
            details[name] = {
                "score": score,
                "passed": passed,
                "weight": weight,
                **grader_details,
            }
            weighted_scores.append((weight, score))
            weighted_passed.append((weight, passed))
        except Exception as exc:
            _report_run_exception(
                exc,
                run_id=context.run.id,
                stage="grader_compare",
                context=context,
                extra_contexts={
                    "row": {
                        "row_index": row_index,
                        "row_keys": sorted(str(key) for key in row_data),
                    },
                    "grader": {"name": name, "weight": weight},
                },
            )
            logger.exception(
                "Run %s grader %s failed on row %s",
                context.run.id,
                name,
                row_index,
            )
            details[name] = {"error": str(exc), "passed": False, "weight": weight}
            weighted_scores.append((weight, 0.0))
            weighted_passed.append((weight, False))

    return _combine_grader_results(details, weighted_scores, weighted_passed)


def _combine_grader_results(
    details: dict[str, dict],
    weighted_scores: list[tuple[float, float]],
    weighted_passed: list[tuple[float, bool | None]],
) -> tuple[float, bool | None, dict]:
    """Reduce individual grader outcomes to one score and pass/fail value."""
    total_weight = sum(weight for weight, _ in weighted_scores if weight > 0)
    if total_weight > 0:
        score = (
            sum(weight * value for weight, value in weighted_scores if weight > 0) / total_weight
        )
    else:
        score = 0.0

    active_passed = [
        passed for weight, passed in weighted_passed if weight > 0 and passed is not None
    ]
    if active_passed:
        return score, all(active_passed), details
    if total_weight > 0:
        return score, None, details
    return score, False, details


async def _cancel_tasks(tasks: list[asyncio.Task[EvalResult]]) -> None:
    """Cancel any unfinished row tasks after a runner failure."""
    for task in tasks:
        if not task.done():
            task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


async def _mark_run_failed(run_id: str, exc: Exception) -> None:
    """Mark a run failed using a fresh session after a top-level runner error."""
    try:
        async with get_session_context() as session:
            await RunRepository(session).update_status(
                run_id,
                status="failed",
                error_message=_format_error_message("Run failed during evaluation", exc),
                completed_at=datetime.now(UTC),
                heartbeat_at=datetime.now(UTC),
            )
    except Exception as mark_failed_exc:
        _report_run_exception(mark_failed_exc, run_id=run_id, stage="mark_run_failed")
        logger.exception("Unable to mark run %s as failed", run_id)


def _format_error_message(context: str, exc: Exception) -> str:
    """Return a bounded run-level failure message suitable for API display."""
    details = str(exc).strip()
    error_type = type(exc).__name__
    message = f"{context}: {error_type}"
    if details:
        message = f"{message}: {details}"
    if len(message) <= MAX_ERROR_MESSAGE_LENGTH:
        return message
    return f"{message[: MAX_ERROR_MESSAGE_LENGTH - 3]}..."


async def _send_slack_notification(
    run_id: str,
    slack_payload: tuple[str, list[dict]] | None,
) -> None:
    """Send a Slack notification after the run commits its final state."""
    if slack_payload is None:
        return

    webhook_url, blocks = slack_payload
    try:
        await slack_notifier.send(webhook_url, blocks)
    except Exception as exc:
        _report_run_exception(exc, run_id=run_id, stage="send_slack_notification")
        logger.exception("Slack notification failed for run %s", run_id)


async def _gather_slack_payload(session, run_id: str) -> tuple[str, list[dict]] | None:
    """Fetch all data needed to build a Slack message for a scheduled run."""
    try:
        run_repo = RunRepository(session)
        run = await run_repo.get_by_id(run_id)
        if run is None:
            return None
        schedule_id = getattr(run, "scheduled_by_id", None)
        if not isinstance(schedule_id, str):
            return None

        schedule = await ScheduleRepository(session).get_by_id(schedule_id)
        if schedule is None:
            return None

        webhook_url = slack_notifier.resolve_webhook_url(schedule.slack_webhook_url)
        if not webhook_url:
            return None

        previous = await run_repo.get_previous_completed_for_schedule(
            schedule.id,
            exclude_run_id=run.id,
        )
        blocks = slack_notifier.build_blocks(
            run=run,
            schedule=schedule,
            previous_run=previous,
        )
        return webhook_url, blocks
    except Exception as exc:
        _report_run_exception(exc, run_id=run_id, stage="build_slack_notification")
        logger.exception("Slack notification skipped for run %s", run_id)
        return None
