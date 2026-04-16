"""Evaluation runner — executes eval runs as background tasks."""

import asyncio
import logging
from datetime import datetime, timezone

from src.comparers.base import BaseComparer
from src.db.models import EvalResult
from src.db.repositories import (
    ConfigRepository,
    DatasetRepository,
    ResultRepository,
    RunRepository,
)
from src.db.session import get_session_context
from src.services.csv_parser import read_csv_rows
from src.services.eval_client import call_llm

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

        # Filter out exceptions and pair results with their source row data
        valid_results: list[EvalResult] = []
        row_data_map: dict[int, dict] = {}  # row_index -> CSV row dict
        for idx, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error("Row processing failed: %s", r)
            else:
                valid_results.append(r)
                row_data_map[r.row_index] = rows[idx]

        # Run comparison pass (lazy import — registry created in T14)
        from src.comparers.registry import get_comparer
        from src.comparers.custom_grader import CustomGraderComparer
        from src.comparers.string_check_grader import StringCheckGraderComparer
        from src.comparers.python_grader import PythonGraderComparer

        # Support multiple comparers (comma-separated in comparer_type)
        comparer_names = [c.strip() for c in config.comparer_type.split(",") if c.strip()]
        comparers: list[tuple[str, BaseComparer]] = [
            (name, get_comparer(name, config.comparer_config))
            for name in comparer_names
        ]

        # Instantiate custom graders based on their type.
        custom_grader_defs: list[dict] = config.custom_graders or []
        for grader_def in custom_grader_defs:
            grader_type = grader_def.get("type", "prompt")
            grader_cfg = {**grader_def}

            if grader_type == "string_check":
                grader = StringCheckGraderComparer(grader_cfg)
            elif grader_type == "python":
                grader = PythonGraderComparer(grader_cfg)
            else:
                # Default: prompt-based LLM grader
                grader_cfg["model"] = grader_def.get("model") or config.model
                grader = CustomGraderComparer(grader_cfg)

            comparers.append((f"custom:{grader.grader_name}", grader))

        # Look up per-comparer weights (default 1.0 for missing keys)
        weights_map: dict[str, float] = config.comparer_weights or {}

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
                        all_details[cname] = {"score": score, "passed": cpassed, "weight": w, **details}
                        weighted_scores.append((w, score))
                        weighted_passed.append((w, cpassed))
                    except Exception as exc:
                        all_details[cname] = {"error": str(exc), "passed": False, "weight": w}
                        weighted_scores.append((w, 0.0))
                        weighted_passed.append((w, False))

                # Weighted mean score: only graders with weight > 0 contribute
                total_weight = sum(w for w, _ in weighted_scores if w > 0)
                if total_weight > 0:
                    result.comparer_score = sum(w * s for w, s in weighted_scores if w > 0) / total_weight
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
            sum(r.latency_ms for r in valid_results if r.latency_ms)
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
            completed_at=datetime.now(timezone.utc),
        )
        logger.info("Run %s completed: %s", run_id, summary)
