"""Dashboard route — app home page."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.app import templates
from ai_eval.db.repositories import RunRepository
from ai_eval.db.session import get_session

router = APIRouter(tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    """Render the dashboard with recent evaluation runs."""
    run_repo = RunRepository(session)
    recent_runs = await run_repo.list_recent(limit=10)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "active_page": "dashboard", "recent_runs": recent_runs},
    )
