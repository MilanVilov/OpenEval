"""CSV export helpers for datasets and evaluation runs."""

from __future__ import annotations

import csv
import json
import re
from io import StringIO

from src.db.models import EvalResult, EvalRun


def build_run_export_csv(run: EvalRun, results: list[EvalResult]) -> str:
    """Build a CSV export for a run and all of its result details."""
    grader_names = _collect_grader_names(results)
    columns = _build_run_export_columns(grader_names)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()

    for result in results:
        row = _build_run_export_row(run, result)
        row.update(_build_grader_columns(result, grader_names))
        writer.writerow(row)

    return buffer.getvalue()


def sanitize_export_name(name: str, *, fallback: str) -> str:
    """Return a filesystem-safe base name for CSV downloads."""
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-._")
    return normalized or fallback


def _collect_grader_names(results: list[EvalResult]) -> list[str]:
    grader_names: set[str] = set()
    for result in results:
        if not isinstance(result.comparer_details, dict):
            continue
        grader_names.update(result.comparer_details.keys())
    return sorted(grader_names)


def _build_run_export_columns(grader_names: list[str]) -> list[str]:
    columns = [
        "run_id",
        "run_status",
        "config_name",
        "dataset_name",
        "run_created_at",
        "run_started_at",
        "run_completed_at",
        "run_summary_json",
        "result_id",
        "row_index",
        "input_data",
        "expected_output",
        "actual_output",
        "passed",
        "comparer_score",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "error",
        "comparer_details_json",
        "token_usage_json",
        "result_created_at",
    ]

    for grader_name in grader_names:
        key = _grader_column_key(grader_name)
        columns.extend(
            [
                f"{key}_score",
                f"{key}_passed",
                f"{key}_reasoning",
                f"{key}_details_json",
            ]
        )

    return columns


def _build_run_export_row(run: EvalRun, result: EvalResult) -> dict[str, str | int | float | bool | None]:
    token_usage = result.token_usage or {}
    return {
        "run_id": run.id,
        "run_status": run.status,
        "config_name": run.config.name if run.config else None,
        "dataset_name": run.dataset.name if run.dataset else None,
        "run_created_at": _format_datetime(run.created_at),
        "run_started_at": _format_datetime(run.started_at),
        "run_completed_at": _format_datetime(run.completed_at),
        "run_summary_json": _json_string(run.summary),
        "result_id": result.id,
        "row_index": result.row_index,
        "input_data": result.input_data,
        "expected_output": result.expected_output,
        "actual_output": result.actual_output,
        "passed": result.passed,
        "comparer_score": result.comparer_score,
        "latency_ms": result.latency_ms,
        "input_tokens": token_usage.get("input_tokens"),
        "output_tokens": token_usage.get("output_tokens"),
        "error": result.error,
        "comparer_details_json": _json_string(result.comparer_details),
        "token_usage_json": _json_string(result.token_usage),
        "result_created_at": _format_datetime(result.created_at),
    }


def _build_grader_columns(
    result: EvalResult, grader_names: list[str]
) -> dict[str, str | int | float | bool | None]:
    if not isinstance(result.comparer_details, dict):
        return {}

    columns: dict[str, str | int | float | bool | None] = {}
    for grader_name in grader_names:
        grader_detail = result.comparer_details.get(grader_name)
        key = _grader_column_key(grader_name)

        if isinstance(grader_detail, dict):
            columns[f"{key}_score"] = grader_detail.get("score")
            columns[f"{key}_passed"] = grader_detail.get("passed")
            columns[f"{key}_reasoning"] = grader_detail.get("reasoning")
            columns[f"{key}_details_json"] = _json_string(grader_detail)
            continue

        columns[f"{key}_details_json"] = _json_string(grader_detail)

    return columns


def _grader_column_key(grader_name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", grader_name).strip("_").lower()
    return f"grader_{sanitized or 'unknown'}"


def _json_string(value: object) -> str:
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _format_datetime(value: object) -> str:
    return "" if value is None else str(value)
