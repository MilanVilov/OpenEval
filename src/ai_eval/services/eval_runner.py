"""Evaluation runner — executes eval runs as background tasks."""

import asyncio
import logging
from datetime import datetime, timezone

from ai_eval.db.models import EvalResult
from ai_eval.db.repositories import (
    ConfigRepository,
    DatasetRepository,
    ResultRepository,
    RunRepository,
)
from ai_eval.db.session import get_session_context
from ai_eval.services.csv_parser import read_csv_rows
from ai_eval.services.eval_client import call_llm

logger = logging.getLogger(__name__)


async def run_evaluation(run_id: str) -> None:
    """Execute an evaluation run.

    This function is designed to be called as a FastAPI BackgroundTask.
    It manages its own DB session.
    """
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
        dataset = await dataset_repo.get_by_id(run.dataset_id)
        if not config or not dataset:
            await run_repo.update_status(run_id, status="failed")
            return

        # Mark as running
        await run_repo.update_status(
            run_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )

        # Read CSV rows
        try:
            rows = await read_csv_rows(dataset.file_path)
        except Exception as exc:
            logger.error("Failed to read dataset: %s", exc)
            await run_repo.update_status(run_id, status="failed")
            return

        await run_repo.update_status(run_id, status="running", total_rows=len(rows))

        # Process rows with concurrency control
        semaphore = asyncio.Semaphore(config.concurrency)
        completed_count = 0

        async def process_row(index: int, row: dict) -> EvalResult:
            """Call the LLM for a single row and return an EvalResult."""
            nonlocal completed_count
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

            completed_count += 1
            try:
                await run_repo.update_progress(run_id, progress=completed_count)
            except Exception:
                pass  # Don't fail the run over a progress update

            return EvalResult(**result_kwargs)

        # Run all rows concurrently
        tasks = [process_row(i, row) for i, row in enumerate(rows)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results: list[EvalResult] = []
        for r in results:
            if isinstance(r, Exception):
                logger.error("Row processing failed: %s", r)
            else:
                valid_results.append(r)

        # Run comparison pass (lazy import — registry created in T14)
        from ai_eval.comparers.registry import get_comparer

        comparer = get_comparer(config.comparer_type, config.comparer_config)

        for result in valid_results:
            if result.actual_output is not None and result.error is None:
                try:
                    score, passed, details = await comparer.compare(
                        expected=result.expected_output,
                        actual=result.actual_output,
                    )
                    result.comparer_score = score
                    result.passed = passed
                    result.comparer_details = details
                except Exception as exc:
                    result.comparer_details = {"error": str(exc)}
                    result.passed = False

        # Batch insert results
        if valid_results:
            await result_repo.create_batch(valid_results)

        # Compute summary statistics
        total = len(valid_results)
        passed = sum(1 for r in valid_results if r.passed)
        failed = sum(1 for r in valid_results if r.passed is False)
        errors = sum(1 for r in valid_results if r.error)
        avg_latency = (
            sum(r.latency_ms for r in valid_results if r.latency_ms)
            / max(total, 1)
        )
        scored = [r for r in valid_results if r.comparer_score is not None]
        avg_score = (
            sum(r.comparer_score for r in scored) / max(len(scored), 1)
        )

        summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "accuracy": passed / max(total, 1),
            "avg_latency_ms": round(avg_latency),
            "avg_score": round(avg_score, 4),
        }

        await run_repo.set_summary(run_id, summary=summary)
        await run_repo.update_status(
            run_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        logger.info("Run %s completed: %s", run_id, summary)
