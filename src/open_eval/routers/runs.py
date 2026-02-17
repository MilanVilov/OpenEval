"""EvalRun CRUD routes — JSON API."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from open_eval.db.repositories import (
    ConfigRepository,
    DatasetRepository,
    ResultRepository,
    RunRepository,
)
from open_eval.db.session import get_session
from open_eval.routers.schemas.runs import (
    CompareResponse,
    CreateRunRequest,
    ResultResponse,
    RunProgressResponse,
    RunResponse,
)
from open_eval.services.csv_export import build_run_export_csv, sanitize_export_name
from open_eval.services.eval_runner import run_evaluation

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _run_to_response(run: object) -> RunResponse:
    """Convert an EvalRun ORM object to a RunResponse."""
    return RunResponse(
        id=run.id,
        eval_config_id=run.eval_config_id,
        dataset_id=run.dataset_id,
        status=run.status,
        progress=run.progress,
        total_rows=run.total_rows,
        summary=run.summary,
        started_at=str(run.started_at) if run.started_at else None,
        completed_at=str(run.completed_at) if run.completed_at else None,
        created_at=str(run.created_at),
        config_name=run.config.name if run.config else None,
        dataset_name=run.dataset.name if run.dataset else None,
    )


def _result_to_response(result: object) -> ResultResponse:
    """Convert an EvalResult ORM object to a ResultResponse."""
    return ResultResponse(
        id=result.id,
        eval_run_id=result.eval_run_id,
        row_index=result.row_index,
        input_data=result.input_data,
        expected_output=result.expected_output,
        actual_output=result.actual_output,
        comparer_score=result.comparer_score,
        comparer_details=result.comparer_details,
        passed=result.passed,
        latency_ms=result.latency_ms,
        token_usage=result.token_usage,
        error=result.error,
        created_at=str(result.created_at),
    )


@router.get("", response_model=list[RunResponse])
async def list_runs(
    session: AsyncSession = Depends(get_session),
) -> list[RunResponse]:
    """List all evaluation runs."""
    runs = await RunRepository(session).list_all()
    return [_run_to_response(r) for r in runs]


@router.post("", response_model=RunResponse, status_code=201)
async def create_run(
    body: CreateRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> RunResponse:
    """Create and start an evaluation run."""
    dataset = await DatasetRepository(session).get_by_id(body.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    config = await ConfigRepository(session).get_by_id(body.eval_config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    run = await RunRepository(session).create(
        eval_config_id=body.eval_config_id,
        dataset_id=body.dataset_id,
        total_rows=dataset.row_count,
    )
    background_tasks.add_task(run_evaluation, run.id)

    # Re-fetch with relationships loaded
    run = await RunRepository(session).get_by_id(run.id)
    return _run_to_response(run)


@router.get("/compare", response_model=CompareResponse)
async def compare_runs(
    run_a: str = "",
    run_b: str = "",
    session: AsyncSession = Depends(get_session),
) -> CompareResponse:
    """Compare two evaluation runs side by side."""
    run_repo = RunRepository(session)
    result_repo = ResultRepository(session)

    response_a = None
    response_b = None
    results_a: list[ResultResponse] = []
    results_b: list[ResultResponse] = []

    if run_a:
        run_obj = await run_repo.get_by_id(run_a)
        if run_obj:
            response_a = _run_to_response(run_obj)
            raw_results = await result_repo.list_by_run(run_a)
            results_a = [_result_to_response(r) for r in raw_results]

    if run_b:
        run_obj = await run_repo.get_by_id(run_b)
        if run_obj:
            response_b = _run_to_response(run_obj)
            raw_results = await result_repo.list_by_run(run_b)
            results_b = [_result_to_response(r) for r in raw_results]

    return CompareResponse(
        run_a=response_a,
        run_b=response_b,
        results_a=results_a,
        results_b=results_b,
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> RunResponse:
    """Return a single evaluation run."""
    run = await RunRepository(session).get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_to_response(run)


@router.get("/{run_id}/progress", response_model=RunProgressResponse)
async def run_progress(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> RunProgressResponse:
    """Return current progress for an eval run."""
    run = await RunRepository(session).get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunProgressResponse(
        status=run.status,
        progress=run.progress,
        total_rows=run.total_rows,
        summary=run.summary,
    )


@router.get("/{run_id}/results", response_model=list[ResultResponse])
async def run_results(
    run_id: str,
    failed_only: bool = False,
    session: AsyncSession = Depends(get_session),
) -> list[ResultResponse]:
    """Return results for an eval run."""
    results = await ResultRepository(session).list_by_run(run_id, failed_only=failed_only)
    return [_result_to_response(r) for r in results]


@router.get("/{run_id}/export")
async def export_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Download a CSV export containing all persisted run results."""
    run_repo = RunRepository(session)
    run = await run_repo.get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    results = await ResultRepository(session).list_by_run(run_id)
    csv_content = build_run_export_csv(run, results)
    export_name = run.config.name if run.config else run.id
    filename = f"{sanitize_export_name(export_name, fallback='evaluation')}-{run.id}.csv"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=csv_content, media_type="text/csv; charset=utf-8", headers=headers)


@router.delete("/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an evaluation run."""
    deleted = await RunRepository(session).delete(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found")
