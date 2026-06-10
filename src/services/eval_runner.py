"""Evaluation runner — executes eval runs as background tasks."""

import asyncio
import logging
from dataclasses import dataclass
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
from src.services.dataset_storage import read_dataset_rows
from src.services.eval_client import call_llm

logger = logging.getLogger(__name__)

MAX_ERROR_MESSAGE_LENGTH = 2000
RESULT_PERSIST_BATCH_SIZE = 1
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


async def run_evaluation(run_id: str) -> None:
    """Execute an evaluation run in a background task."""
    try:
        await _run_evaluation(run_id)
    except Exception as exc:
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
            rows = await _read_rows(context.run_repo, run_id, context.dataset)
            if rows is None:
                return

            await context.run_repo.update_status(
                run_id,
                status="running",
                total_rows=len(rows),
                heartbeat_at=datetime.now(UTC),
            )
            grader_bundle = _build_grader_bundle(context.config)
            results = await _process_rows(context, rows, grader_bundle)
            summary = await _mark_run_completed(context.run_repo, run_id, results)
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
    run_repo: RunRepository,
    run_id: str,
    dataset: Dataset,
) -> list[dict] | None:
    """Load CSV rows for a run or mark the run failed."""
    try:
        return await read_dataset_rows(dataset)
    except Exception as exc:
        logger.error("Failed to read dataset for run %s: %s", run_id, exc)
        await run_repo.update_status(
            run_id,
            status="failed",
            error_message=_format_error_message("Failed to read dataset", exc),
            completed_at=datetime.now(UTC),
            heartbeat_at=datetime.now(UTC),
        )
        return None


def _build_grader_bundle(config: EvalConfig) -> GraderBundle:
    """Instantiate graders and collect their configured weights."""
    comparers: list[tuple[str, BaseComparer]] = []
    weights: dict[str, float] = {}
    for grader_def in config.graders or []:
        grader = _build_grader(grader_def, config.model)
        comparers.append((grader.grader_name, grader))
        weights[grader.grader_name] = grader_def.get("weight", 1.0)
    return GraderBundle(comparers=comparers, weights=weights)


def _build_grader(grader_def: dict, default_model: str) -> BaseComparer:
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
    return CustomGraderComparer(grader_cfg)


async def _process_rows(
    context: RunExecutionContext,
    rows: list[dict],
    grader_bundle: GraderBundle,
) -> list[EvalResult]:
    """Process all rows and persist committed result batches incrementally."""
    semaphore = asyncio.Semaphore(context.config.concurrency)
    tasks = [
        asyncio.create_task(
            _process_row(context.run.id, index, row, context, grader_bundle, semaphore)
        )
        for index, row in enumerate(rows)
    ]
    persisted_results: list[EvalResult] = []
    pending_results: list[EvalResult] = []
    committed_count = 0

    try:
        for task in asyncio.as_completed(tasks):
            pending_results.append(await task)
            if len(pending_results) < RESULT_PERSIST_BATCH_SIZE:
                continue
            committed_count = await _flush_result_batch(
                context,
                pending_results,
                committed_count,
                persisted_results,
            )
            pending_results = []
        if pending_results:
            await _flush_result_batch(
                context,
                pending_results,
                committed_count,
                persisted_results,
            )
        return persisted_results
    except Exception:
        await _cancel_tasks(tasks)
        raise


async def _process_row(
    run_id: str,
    index: int,
    row: dict,
    context: RunExecutionContext,
    grader_bundle: GraderBundle,
    semaphore: asyncio.Semaphore,
) -> EvalResult:
    """Process one row through the provider and grader pipeline."""
    result = _build_result(run_id, index, row)
    async with semaphore:
        await _populate_row_result(result, row, context, grader_bundle)
    return result


async def _flush_result_batch(
    context: RunExecutionContext,
    pending_results: list[EvalResult],
    committed_count: int,
    persisted_results: list[EvalResult],
) -> int:
    """Persist one result batch and advance progress only after commit succeeds."""
    await context.result_repo.upsert_batch(pending_results)
    persisted_results.extend(pending_results)
    committed_count += len(pending_results)
    await context.run_repo.update_progress(
        context.run.id,
        progress=committed_count,
        heartbeat_at=datetime.now(UTC),
    )
    return committed_count


async def _mark_run_completed(
    run_repo: RunRepository,
    run_id: str,
    results: list[EvalResult],
) -> dict:
    """Store the final summary and mark the run completed."""
    now = datetime.now(UTC)
    summary = _build_summary(results)
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
        )
        result.actual_output = llm_response.text
        result.latency_ms = llm_response.latency_ms
        result.token_usage = llm_response.token_usage
        (
            result.comparer_score,
            result.passed,
            result.comparer_details,
        ) = await _apply_graders(
            grader_bundle,
            expected=result.expected_output,
            actual=llm_response.text,
            row_data=row,
        )
    except Exception as exc:
        result.error = str(exc)


async def _apply_graders(
    grader_bundle: GraderBundle,
    *,
    expected: str,
    actual: str,
    row_data: dict,
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
            sum(weight * value for weight, value in weighted_scores if weight > 0)
            / total_weight
        )
    else:
        score = 0.0

    active_passed = [
        passed
        for weight, passed in weighted_passed
        if weight > 0 and passed is not None
    ]
    if active_passed:
        return score, all(active_passed), details
    if total_weight > 0:
        return score, None, details
    return score, False, details


def _build_summary(results: list[EvalResult]) -> dict:
    """Build the run summary JSON from all row results."""
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    failed = sum(1 for result in results if result.passed is False)
    unjudged = sum(1 for result in results if result.passed is None and not result.error)
    errors = sum(1 for result in results if result.error)
    scored = [result.comparer_score for result in results if result.comparer_score is not None]
    avg_score = sum(scored) / max(len(scored), 1)
    avg_input_tokens, avg_output_tokens = _average_token_usage(results)
    judged = passed + failed
    return {
        "total": total,
        "judged": judged,
        "passed": passed,
        "failed": failed,
        "unjudged": unjudged,
        "errors": errors,
        "accuracy": passed / max(judged + errors, 1),
        "avg_latency_ms": _average_latency(results),
        "avg_score": round(avg_score, 4),
        "avg_input_tokens": avg_input_tokens,
        "avg_output_tokens": avg_output_tokens,
        "grader_stats": _build_grader_stats(results),
    }


def _average_latency(results: list[EvalResult]) -> int:
    """Return the mean latency across all result rows."""
    total_latency = sum(result.latency_ms or 0 for result in results)
    return round(total_latency / max(len(results), 1))


def _average_token_usage(results: list[EvalResult]) -> tuple[int, int]:
    """Return average input and output tokens across rows with usage data."""
    input_tokens = [
        result.token_usage["input_tokens"]
        for result in results
        if result.token_usage and "input_tokens" in result.token_usage
    ]
    output_tokens = [
        result.token_usage["output_tokens"]
        for result in results
        if result.token_usage and "output_tokens" in result.token_usage
    ]
    avg_input = round(sum(input_tokens) / len(input_tokens)) if input_tokens else 0
    avg_output = round(sum(output_tokens) / len(output_tokens)) if output_tokens else 0
    return avg_input, avg_output


def _build_grader_stats(results: list[EvalResult]) -> dict[str, dict]:
    """Aggregate pass/fail counts and average scores per grader."""
    grader_stats: dict[str, dict] = {}
    for result in results:
        for name, detail in (result.comparer_details or {}).items():
            if not isinstance(detail, dict):
                continue
            stats = grader_stats.setdefault(name, _new_grader_stats())
            stats["total"] += 1
            if detail.get("passed") is True:
                stats["passed"] += 1
            elif detail.get("passed") is False:
                stats["failed"] += 1
            else:
                stats["unjudged"] += 1
            if isinstance(detail.get("score"), (int, float)):
                stats["scores"].append(detail["score"])

    for stats in grader_stats.values():
        scores = stats.pop("scores")
        judged = stats["passed"] + stats["failed"]
        stats["judged"] = judged
        stats["accuracy"] = stats["passed"] / max(judged, 1)
        stats["avg_score"] = round(sum(scores) / len(scores), 4) if scores else 0.0
    return grader_stats


def _new_grader_stats() -> dict:
    """Return the initial accumulator structure for one grader."""
    return {"total": 0, "passed": 0, "failed": 0, "unjudged": 0, "scores": []}


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
        logger.warning("Heartbeat update failed for run %s: %s", run_id, exc)


async def _stop_heartbeat(
    stop_event: asyncio.Event,
    heartbeat_task: asyncio.Task[None],
) -> None:
    """Stop the heartbeat loop and wait for it to exit cleanly."""
    stop_event.set()
    await heartbeat_task


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
    except Exception:
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
        logger.warning("Slack notification failed for run %s: %s", run_id, exc)


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
        logger.warning("Slack notification skipped for run %s: %s", run_id, exc)
        return None
