"""EvalRun CRUD routes."""

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.app import templates
from ai_eval.db.repositories import ConfigRepository, DatasetRepository, ResultRepository, RunRepository
from ai_eval.db.session import get_session
from ai_eval.services.eval_runner import run_evaluation

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_class=HTMLResponse)
async def list_runs(request: Request, session: AsyncSession = Depends(get_session)):
    """List all evaluation runs."""
    runs = await RunRepository(session).list_all()
    return templates.TemplateResponse(
        "runs/list.html",
        {"request": request, "active_page": "runs", "runs": runs},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_run(request: Request, session: AsyncSession = Depends(get_session)):
    """Render the create-run form."""
    configs = await ConfigRepository(session).list_all()
    datasets = await DatasetRepository(session).list_all()
    return templates.TemplateResponse(
        "runs/new.html",
        {"request": request, "active_page": "runs", "configs": configs, "datasets": datasets},
    )


@router.get("/compare", response_class=HTMLResponse)
async def compare_runs(
    request: Request,
    session: AsyncSession = Depends(get_session),
    run_a: str = "",
    run_b: str = "",
):
    """Compare two evaluation runs side by side."""
    runs = await RunRepository(session).list_all()

    result_a = None
    result_b = None
    results_a: list = []
    results_b: list = []

    if run_a:
        result_a = await RunRepository(session).get_by_id(run_a)
        if result_a:
            results_a = await ResultRepository(session).list_by_run(run_a)

    if run_b:
        result_b = await RunRepository(session).get_by_id(run_b)
        if result_b:
            results_b = await ResultRepository(session).list_by_run(run_b)

    return templates.TemplateResponse(
        "runs/compare.html",
        {
            "request": request,
            "active_page": "runs",
            "runs": runs,
            "run_a": result_a,
            "run_b": result_b,
            "results_a": results_a,
            "results_b": results_b,
            "selected_a": run_a,
            "selected_b": run_b,
        },
    )


@router.post("", response_class=HTMLResponse)
async def create_run(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    eval_config_id: str = Form(...),
    dataset_id: str = Form(...),
):
    """Create and start an evaluation run."""
    dataset = await DatasetRepository(session).get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    config = await ConfigRepository(session).get_by_id(eval_config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    run = await RunRepository(session).create(
        eval_config_id=eval_config_id,
        dataset_id=dataset_id,
        total_rows=dataset.row_count,
    )
    background_tasks.add_task(run_evaluation, run.id)
    return RedirectResponse(f"/runs/{run.id}", status_code=303)


@router.get("/{run_id}", response_class=HTMLResponse)
async def detail_run(
    run_id: str, request: Request, session: AsyncSession = Depends(get_session),
):
    """Show a single evaluation run."""
    run = await RunRepository(session).get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return templates.TemplateResponse(
        "runs/detail.html",
        {"request": request, "active_page": "runs", "run": run},
    )


@router.get("/{run_id}/progress", response_class=HTMLResponse)
async def run_progress(
    run_id: str, request: Request, session: AsyncSession = Depends(get_session),
):
    """Return progress fragment for HTMX polling."""
    run = await RunRepository(session).get_by_id(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return templates.TemplateResponse(
        "runs/partials/progress.html",
        {"request": request, "run": run},
    )


@router.get("/{run_id}/results", response_class=HTMLResponse)
async def run_results(
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    failed_only: bool = False,
):
    """Return results table fragment for HTMX."""
    results = await ResultRepository(session).list_by_run(run_id, failed_only=failed_only)
    return templates.TemplateResponse(
        "runs/partials/results.html",
        {"request": request, "results": results, "failed_only": failed_only, "run_id": run_id},
    )


@router.delete("/{run_id}")
async def delete_run(
    run_id: str, session: AsyncSession = Depends(get_session),
):
    """Delete an evaluation run."""
    deleted = await RunRepository(session).delete(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found")
    return Response(status_code=200, headers={"HX-Redirect": "/runs"})
