"""Pydantic schemas for Schedule endpoints."""

from pydantic import BaseModel, Field


class ScheduleBase(BaseModel):
    """Fields shared between create and update payloads."""

    name: str = Field(min_length=1, max_length=200)
    eval_config_id: str
    dataset_id: str
    cron_expression: str = Field(min_length=1, max_length=120)
    enabled: bool = True
    slack_webhook_url: str | None = None
    min_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)


class ScheduleCreate(ScheduleBase):
    """Request body for creating a schedule."""


class ScheduleUpdate(BaseModel):
    """Request body for updating a schedule. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    eval_config_id: str | None = None
    dataset_id: str | None = None
    cron_expression: str | None = Field(default=None, min_length=1, max_length=120)
    enabled: bool | None = None
    slack_webhook_url: str | None = None
    min_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)


class LastRunSummary(BaseModel):
    """Compact summary of a schedule's most recent run."""

    id: str
    status: str
    accuracy: float | None
    completed_at: str | None


class ScheduleResponse(BaseModel):
    """Response model for a schedule."""

    id: str
    name: str
    eval_config_id: str
    dataset_id: str
    cron_expression: str
    enabled: bool
    slack_webhook_url: str | None
    min_accuracy: float | None
    last_triggered_at: str | None
    next_run_at: str | None
    created_at: str
    updated_at: str
    config_name: str | None = None
    dataset_name: str | None = None
    last_run: LastRunSummary | None = None

    model_config = {"from_attributes": True}
