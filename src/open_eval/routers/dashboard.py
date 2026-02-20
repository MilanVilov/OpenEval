"""Dashboard route — JSON API for dashboard summary data."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from open_eval.db.repositories import RunRepository
from open_eval.db.session import get_session
from open_eval.routers.schemas.dashboard import DashboardResponse
from open_eval.routers.schemas.runs import RunResponse

router = APIRouter(prefix="/api", tags=["dashboard"])


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


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(session: AsyncSession = Depends(get_session)) -> DashboardResponse:
    """Return dashboard summary data as JSON."""
    run_repo = RunRepository(session)
    recent_runs = await run_repo.list_recent(limit=10)
    return DashboardResponse(
        recent_runs=[_run_to_response(r) for r in recent_runs],
    )
