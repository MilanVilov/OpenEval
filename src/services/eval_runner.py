"""Evaluation runner — executes eval runs as background tasks."""

import asyncio
import logging
<<<<<<< Updated upstream
=======
from dataclasses import dataclass
>>>>>>> Stashed changes
from datetime import UTC, datetime

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
    except Exception:
        logger.exception("Run %s crashed during execution", run_id)
        await _mark_run_failed(run_id)

<<<<<<< Updated upstream
    This function is designed to be called as a FastAPI BackgroundTask.
    It manages its own DB session.
    """
    slack_payload: tuple[str, list[dict]] | None = None
    try:
        async with get_session_context() as session:
            run_repo = RunRepository(session)
            config_repo = ConfigRepository(session)
            result_repo = ResultRepository(session)
            dataset_repo = DatasetRepository(session)

            run = await run_repo.get_by_id(run_id)
            if not run:
                logger.error("Run %s not found", run_id)
                return

            config = await config_repo.get_by_id(run.eval_config_id)
            dataset = await dataset_repo.get_by_id_with_content(run.dataset_id)
            if not config or not dataset:
                await run_repo.update_status(
                    run_id,
                    status="failed",
                    error_message="Run failed because the referenced config or dataset was not found.",
                    completed_at=datetime.now(UTC),
                )
                return

            # Mark as running
            await run_repo.update_status(
                run_id,
                status="running",
                error_message=None,
                started_at=datetime.now(UTC),
            )

            # Read CSV rows
            try:
                rows = await read_dataset_rows(dataset)
            except Exception as exc:
                logger.error("Failed to read dataset: %s", exc)
                await run_repo.update_status(
                    run_id,
                    status="failed",
                    error_message=_format_error_message("Failed to read dataset", exc),
                    completed_at=datetime.now(UTC),
                )
                return

            await run_repo.update_status(run_id, status="running", total_rows=len(rows))

            # Process rows with concurrency control
            semaphore = asyncio.Semaphore(config.concurrency)

            async def process_row(index: int, row: dict) -> EvalResult:
                """Call the LLM for a single row and return an EvalResult."""
                user_input = row.get("input", "")
                expected = row.get("expected_output", "")

                result_kwargs: dict = {
                    "eval_run_id": run_id,
                    "row_index": index,
                    "input_data": user_input,
                    "expected_output": expected,
                }

                async with semaphore:
                    try:
                        llm_response = await call_llm(
                            system_prompt=config.system_prompt,
                            user_input=user_input,
                            model=config.model,
                            temperature=config.temperature,
                            max_tokens=config.max_tokens,
                            tools=config.tools,
                            tool_options=config.tool_options,
                            reasoning_config=config.reasoning_config,
                            response_format=config.response_format,
                        )
                        result_kwargs["actual_output"] = llm_response.text
                        result_kwargs["latency_ms"] = llm_response.latency_ms
                        result_kwargs["token_usage"] = llm_response.token_usage
                    except Exception as exc:
                        result_kwargs["error"] = str(exc)

                return EvalResult(**result_kwargs)

            # Run all rows concurrently. Progress updates happen in this parent
            # coroutine so the shared DB session is never used by row tasks.
            tasks = [asyncio.create_task(process_row(i, row)) for i, row in enumerate(rows)]
            results: list[EvalResult | Exception] = []
            for completed_count, task in enumerate(asyncio.as_completed(tasks), start=1):
                try:
                    results.append(await task)
                except Exception as exc:
                    results.append(exc)
                try:
                    await run_repo.update_progress(run_id, progress=completed_count)
                except Exception as exc:
                    logger.warning("Progress update failed for run %s: %s", run_id, exc)
                    await session.rollback()

            # Filter out exceptions and pair results with their source row data
            valid_results: list[EvalResult] = []
            row_data_map: dict[int, dict] = {}  # row_index -> CSV row dict
            for r in results:
                if isinstance(r, Exception):
                    logger.error("Row processing failed: %s", r)
                else:
                    valid_results.append(r)
                    row_data_map[r.row_index] = rows[r.row_index]

            # Instantiate graders from the unified graders list
            from src.comparers.custom_grader import CustomGraderComparer
            from src.comparers.json_field_match import JsonFieldMatchComparer
            from src.comparers.json_schema_match import JsonSchemaMatchComparer
            from src.comparers.python_grader import PythonGraderComparer
            from src.comparers.semantic_similarity import SemanticSimilarityComparer
            from src.comparers.string_check_grader import StringCheckGraderComparer

            grader_defs: list[dict] = config.graders or []
            comparers: list[tuple[str, BaseComparer]] = []
            for grader_def in grader_defs:
                grader_type = grader_def.get("type", "prompt")
                grader_cfg = {**grader_def}

                if grader_type == "string_check":
                    grader = StringCheckGraderComparer(grader_cfg)
                elif grader_type == "python":
                    grader = PythonGraderComparer(grader_cfg)
                elif grader_type == "semantic_similarity":
                    grader = SemanticSimilarityComparer(grader_cfg)
                elif grader_type == "json_schema":
                    grader = JsonSchemaMatchComparer(grader_cfg)
                elif grader_type == "json_field":
                    grader = JsonFieldMatchComparer(grader_cfg)
                else:
                    # Default: prompt-based LLM grader
                    grader_cfg["model"] = grader_def.get("model") or config.model
                    grader = CustomGraderComparer(grader_cfg)

                comparers.append((grader.grader_name, grader))

            # Build per-grader weight lookup from grader definitions
            weights_map: dict[str, float] = {}
            for grader_def in grader_defs:
                gname = grader_def.get("name", "")
                weights_map[gname] = grader_def.get("weight", 1.0)

            for result in valid_results:
                if result.actual_output is not None and result.error is None:
                    all_details: dict = {}
                    weighted_scores: list[tuple[float, float]] = []  # (weight, score)
                    weighted_passed: list[tuple[float, bool]] = []   # (weight, passed)
                    row = row_data_map.get(result.row_index)

                    for cname, comparer in comparers:
                        w = weights_map.get(cname, 1.0)
                        try:
                            score, cpassed, details = await comparer.compare(
                                expected=result.expected_output,
                                actual=result.actual_output,
                                row_data=row,
                            )
                            all_details[cname] = {
                                "score": score,
                                "passed": cpassed,
                                "weight": w,
                                **details,
                            }
                            weighted_scores.append((w, score))
                            weighted_passed.append((w, cpassed))
                        except Exception as exc:
                            all_details[cname] = {"error": str(exc), "passed": False, "weight": w}
                            weighted_scores.append((w, 0.0))
                            weighted_passed.append((w, False))

                    # Weighted mean score: only graders with weight > 0 contribute
                    total_weight = sum(w for w, _ in weighted_scores if w > 0)
                    if total_weight > 0:
                        result.comparer_score = (
                            sum(w * s for w, s in weighted_scores if w > 0) / total_weight
                        )
                    else:
                        result.comparer_score = 0.0

                    # Pass/fail: AND of all graders with weight > 0; weight=0 is informational
                    active_passed = [p for w, p in weighted_passed if w > 0]
                    result.passed = all(active_passed) if active_passed else False
                    result.comparer_details = all_details

            # Batch insert results
            if valid_results:
                await result_repo.create_batch(valid_results)

            # Compute summary statistics
            total = len(valid_results)
            passed = sum(1 for r in valid_results if r.passed)
            failed = sum(1 for r in valid_results if r.passed is False)
            errors = sum(1 for r in valid_results if r.error)
            avg_latency = (
                sum(r.latency_ms for r in valid_results if r.latency_ms is not None)
                / max(total, 1)
            )
            scored = [r for r in valid_results if r.comparer_score is not None]
            avg_score = (
                sum(r.comparer_score for r in scored) / max(len(scored), 1)
            )

            # Compute average token usage
            input_tokens_list = [
                r.token_usage["input_tokens"]
                for r in valid_results
                if r.token_usage and "input_tokens" in r.token_usage
            ]
            output_tokens_list = [
                r.token_usage["output_tokens"]
                for r in valid_results
                if r.token_usage and "output_tokens" in r.token_usage
            ]
            avg_input_tokens = (
                round(sum(input_tokens_list) / len(input_tokens_list))
                if input_tokens_list
                else 0
            )
            avg_output_tokens = (
                round(sum(output_tokens_list) / len(output_tokens_list))
                if output_tokens_list
                else 0
            )

            # Compute per-grader statistics
            grader_stats: dict[str, dict] = {}
            for r in valid_results:
                if not r.comparer_details:
                    continue
                for gname, detail in r.comparer_details.items():
                    if not isinstance(detail, dict):
                        continue
                    if gname not in grader_stats:
                        grader_stats[gname] = {
                            "total": 0,
                            "passed": 0,
                            "failed": 0,
                            "scores": [],
                        }
                    stats = grader_stats[gname]
                    stats["total"] += 1
                    if detail.get("passed"):
                        stats["passed"] += 1
                    else:
                        stats["failed"] += 1
                    if isinstance(detail.get("score"), (int, float)):
                        stats["scores"].append(detail["score"])

            # Finalize grader_stats: compute accuracy and avg_score, drop raw scores
            for stats in grader_stats.values():
                scores = stats.pop("scores")
                stats["accuracy"] = stats["passed"] / max(stats["total"], 1)
                stats["avg_score"] = (
                    round(sum(scores) / len(scores), 4) if scores else 0.0
                )

            summary = {
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "accuracy": passed / max(total, 1),
                "avg_latency_ms": round(avg_latency),
                "avg_score": round(avg_score, 4),
                "avg_input_tokens": avg_input_tokens,
                "avg_output_tokens": avg_output_tokens,
                "grader_stats": grader_stats,
            }

            await run_repo.set_summary(run_id, summary=summary)
            await run_repo.update_status(
                run_id,
                status="completed",
                error_message=None,
                completed_at=datetime.now(UTC),
            )
            logger.info("Run %s completed: %s", run_id, summary)

            slack_payload = await _gather_slack_payload(session, run_id)

    except Exception as exc:
        logger.exception("Run %s failed during evaluation", run_id)
        await _mark_run_failed(run_id, exc)
        return
=======

async def _run_evaluation(run_id: str) -> None:
    """Execute one run from row loading through summary generation."""
    async with get_session_context() as session:
        context = await _load_run_context(session, run_id)
        if context is None:
            return

        await _mark_run_started(context.run_repo, run_id)
        rows = await _read_rows(context.run_repo, run_id, context.dataset)
        if rows is None:
            return

        await context.run_repo.update_status(run_id, status="running", total_rows=len(rows))
        grader_bundle = _build_grader_bundle(context.config)
        results = await _process_rows(context, rows, grader_bundle)

        await context.run_repo.update_status(run_id, status="finalizing")
        if results:
            await context.result_repo.create_batch(results)

        summary = _build_summary(results)
        await context.run_repo.set_summary(run_id, summary=summary)
        await context.run_repo.update_status(
            run_id,
            status="completed",
            completed_at=datetime.now(UTC),
        )
        logger.info("Run %s completed: %s", run_id, summary)
        slack_payload = await _gather_slack_payload(session, run_id)
>>>>>>> Stashed changes

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
        await run_repo.update_status(run_id, status="failed")
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
    await run_repo.update_status(
        run_id,
        status="running",
        started_at=datetime.now(UTC),
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
        await run_repo.update_status(run_id, status="failed")
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
    """Process all rows with bounded concurrency and accurate progress updates."""
    semaphore = asyncio.Semaphore(context.config.concurrency)
    progress_lock = asyncio.Lock()
    completed_count = 0

    async def record_progress() -> None:
        nonlocal completed_count
        async with progress_lock:
            completed_count += 1
            try:
                await context.run_repo.update_progress(context.run.id, progress=completed_count)
            except Exception as exc:
                logger.warning("Progress update failed for run %s: %s", context.run.id, exc)

    async def process_row(index: int, row: dict) -> EvalResult:
        result = _build_result(context.run.id, index, row)
        async with semaphore:
            await _populate_row_result(result, row, context, grader_bundle)
        await record_progress()
        return result

    tasks = [process_row(index, row) for index, row in enumerate(rows)]
    return await asyncio.gather(*tasks)


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
) -> tuple[float, bool, dict]:
    """Run all configured graders for one row and combine their outputs."""
    details: dict[str, dict] = {}
    weighted_scores: list[tuple[float, float]] = []
    weighted_passed: list[tuple[float, bool]] = []

    for name, comparer in grader_bundle.comparers:
        weight = grader_bundle.weights.get(name, 1.0)
        try:
<<<<<<< Updated upstream
            await slack_notifier.send(webhook_url, blocks)
        except Exception as exc:
            logger.warning("Slack notification failed for run %s: %s", run_id, exc)
=======
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
    weighted_passed: list[tuple[float, bool]],
) -> tuple[float, bool, dict]:
    """Reduce individual grader outcomes to one score and pass/fail value."""
    total_weight = sum(weight for weight, _ in weighted_scores if weight > 0)
    if total_weight > 0:
        score = (
            sum(weight * value for weight, value in weighted_scores if weight > 0)
            / total_weight
        )
    else:
        score = 0.0

    active_passed = [passed for weight, passed in weighted_passed if weight > 0]
    return score, all(active_passed) if active_passed else False, details


def _build_summary(results: list[EvalResult]) -> dict:
    """Build the run summary JSON from all row results."""
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    failed = sum(1 for result in results if result.passed is False)
    errors = sum(1 for result in results if result.error)
    scored = [result.comparer_score for result in results if result.comparer_score is not None]
    avg_score = sum(scored) / max(len(scored), 1)
    avg_input_tokens, avg_output_tokens = _average_token_usage(results)
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "accuracy": passed / max(total, 1),
        "avg_latency_ms": _average_latency(results),
        "avg_score": round(avg_score, 4),
        "avg_input_tokens": avg_input_tokens,
        "avg_output_tokens": avg_output_tokens,
        "grader_stats": _build_grader_stats(results),
    }


def _average_latency(results: list[EvalResult]) -> int:
    """Return the mean latency across all result rows."""
    total_latency = sum(result.latency_ms for result in results if result.latency_ms)
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
            if detail.get("passed"):
                stats["passed"] += 1
            else:
                stats["failed"] += 1
            if isinstance(detail.get("score"), (int, float)):
                stats["scores"].append(detail["score"])

    for stats in grader_stats.values():
        scores = stats.pop("scores")
        stats["accuracy"] = stats["passed"] / max(stats["total"], 1)
        stats["avg_score"] = round(sum(scores) / len(scores), 4) if scores else 0.0
    return grader_stats


def _new_grader_stats() -> dict:
    """Return the initial accumulator structure for one grader."""
    return {"total": 0, "passed": 0, "failed": 0, "scores": []}


async def _mark_run_failed(run_id: str) -> None:
    """Mark a run failed after an unexpected top-level error."""
    try:
        async with get_session_context() as session:
            await RunRepository(session).update_status(
                run_id,
                status="failed",
                completed_at=datetime.now(UTC),
            )
    except Exception:
        logger.exception("Unable to mark run %s as failed", run_id)


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
>>>>>>> Stashed changes


async def _mark_run_failed(run_id: str, exc: Exception) -> None:
    """Mark a run failed using a fresh session after runner finalization errors."""
    try:
        async with get_session_context() as session:
            await RunRepository(session).update_status(
                run_id,
                status="failed",
                error_message=_format_error_message("Run failed during evaluation", exc),
                completed_at=datetime.now(UTC),
            )
    except Exception:
        logger.exception("Failed to mark run %s as failed after error: %s", run_id, exc)


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


async def _gather_slack_payload(session, run_id: str) -> tuple[str, list[dict]] | None:
    """Fetch all data needed to build a Slack message for a scheduled run.

    Returns ``(webhook_url, blocks)`` or ``None`` if no notification should
    be sent. Never raises — errors are logged and treated as "skip".
    """
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
            schedule.id, exclude_run_id=run.id,
        )
        blocks = slack_notifier.build_blocks(
            run=run, schedule=schedule, previous_run=previous,
        )
        return webhook_url, blocks
    except Exception as exc:
        logger.warning("Slack notification skipped for run %s: %s", run_id, exc)
        return None
