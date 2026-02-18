"""Pydantic schemas for Dashboard endpoint."""

from pydantic import BaseModel

from ai_eval.routers.schemas.runs import RunResponse


class DashboardResponse(BaseModel):
    """Response model for the dashboard summary."""

    recent_runs: list[RunResponse]
