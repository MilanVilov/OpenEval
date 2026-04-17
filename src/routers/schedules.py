"""Schedule CRUD routes — JSON API."""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Schedule
from src.db.repositories import (
    ConfigRepository,
    DatasetRepository,
    RunRepository,
    ScheduleRepository,
)
from src.db.session import get_session
from src.routers.schemas.schedules import (
    LastRunSummary,
    ScheduleCreate,
    ScheduleResponse,
    ScheduleUpdate,
)
from src.services.eval_runner import run_evaluation
from src.services.scheduler import get_scheduler_service, is_valid_cron

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


async def _schedule_to_response(
    schedule: Schedule, session: AsyncSession,
) -> ScheduleResponse:
    """Convert a :class:`Schedule` ORM object to a response payload."""
    scheduler = get_scheduler_service()
    next_run = scheduler.get_next_run_at(schedule)
    latest = await RunRepository(session).get_latest_for_schedule(schedule.id)

    last_run = None
    if latest is not None:
        summary = latest.summary or {}
        accuracy = summary.get("accuracy") if isinstance(summary, dict) else None
        last_run = LastRunSummary(
            id=latest.id,
            status=latest.status,
            accuracy=accuracy if isinstance(accuracy, (int, float)) else None,
            completed_at=str(latest.completed_at) if latest.completed_at else None,
        )

    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        eval_config_id=schedule.eval_config_id,
        dataset_id=schedule.dataset_id,
        cron_expression=schedule.cron_expression,
        enabled=schedule.enabled,
        slack_webhook_url=schedule.slack_webhook_url,
        min_accuracy=schedule.min_accuracy,
        last_triggered_at=(
            str(schedule.last_triggered_at) if schedule.last_triggered_at else None
        ),
        next_run_at=str(next_run) if next_run else None,
        created_at=str(schedule.created_at),
        updated_at=str(schedule.updated_at),
        config_name=schedule.config.name if schedule.config else None,
        dataset_name=schedule.dataset.name if schedule.dataset else None,
        last_run=last_run,
    )


def _validate_cron(expression: str) -> None:
    """Raise HTTP 422 if ``expression`` is not a valid cron."""
    if not is_valid_cron(expression):
        raise HTTPException(
            status_code=422, detail=f"Invalid cron expression: {expression!r}",
        )


async def _assert_refs_exist(
    body_config_id: str | None,
    body_dataset_id: str | None,
    session: AsyncSession,
) -> None:
    """Raise HTTP 404 if referenced config or dataset does not exist."""
    if body_config_id is not None:
        if await ConfigRepository(session).get_by_id(body_config_id) is None:
            raise HTTPException(status_code=404, detail="Config not found")
    if body_dataset_id is not None:
        if await DatasetRepository(session).get_by_id(body_dataset_id) is None:
            raise HTTPException(status_code=404, detail="Dataset not found")


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(
    session: AsyncSession = Depends(get_session),
) -> list[ScheduleResponse]:
    """List all schedules."""
    schedules = await ScheduleRepository(session).list_all()
    return [await _schedule_to_response(s, session) for s in schedules]


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    body: ScheduleCreate,
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    """Create a new schedule."""
    _validate_cron(body.cron_expression)
    await _assert_refs_exist(body.eval_config_id, body.dataset_id, session)

    repo = ScheduleRepository(session)
    schedule = await repo.create(
        name=body.name,
        eval_config_id=body.eval_config_id,
        dataset_id=body.dataset_id,
        cron_expression=body.cron_expression,
        enabled=body.enabled,
        slack_webhook_url=body.slack_webhook_url or None,
        min_accuracy=body.min_accuracy,
    )
    # Re-fetch with relationships eager-loaded
    schedule = await repo.get_by_id(schedule.id)
    assert schedule is not None
    get_scheduler_service().sync_schedule(schedule)
    return await _schedule_to_response(schedule, session)


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    """Return a single schedule."""
    schedule = await ScheduleRepository(session).get_by_id(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return await _schedule_to_response(schedule, session)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    body: ScheduleUpdate,
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    """Update an existing schedule."""
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=422, detail="No fields to update")
    if "cron_expression" in fields:
        _validate_cron(fields["cron_expression"])
    await _assert_refs_exist(
        fields.get("eval_config_id"), fields.get("dataset_id"), session,
    )
    if "slack_webhook_url" in fields and fields["slack_webhook_url"] == "":
        fields["slack_webhook_url"] = None

    repo = ScheduleRepository(session)
    schedule = await repo.update(schedule_id, **fields)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedule = await repo.get_by_id(schedule.id)
    assert schedule is not None
    get_scheduler_service().sync_schedule(schedule)
    return await _schedule_to_response(schedule, session)


@router.post("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: str,
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    """Flip ``enabled`` on a schedule."""
    repo = ScheduleRepository(session)
    schedule = await repo.get_by_id(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await repo.update(schedule_id, enabled=not schedule.enabled)
    schedule = await repo.get_by_id(schedule_id)
    assert schedule is not None
    get_scheduler_service().sync_schedule(schedule)
    return await _schedule_to_response(schedule, session)


@router.post("/{schedule_id}/run-now", response_model=ScheduleResponse)
async def run_schedule_now(
    schedule_id: str,
    session: AsyncSession = Depends(get_session),
) -> ScheduleResponse:
    """Trigger an immediate run for a schedule (does not alter cron timing)."""
    schedule_repo = ScheduleRepository(session)
    schedule = await schedule_repo.get_by_id(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    dataset = await DatasetRepository(session).get_by_id(schedule.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if await ConfigRepository(session).get_by_id(schedule.eval_config_id) is None:
        raise HTTPException(status_code=404, detail="Config not found")

    run = await RunRepository(session).create(
        eval_config_id=schedule.eval_config_id,
        dataset_id=schedule.dataset_id,
        total_rows=dataset.row_count,
        scheduled_by_id=schedule.id,
    )
    await schedule_repo.mark_triggered(schedule.id, when=datetime.now(UTC))
    asyncio.create_task(run_evaluation(run.id))

    schedule = await schedule_repo.get_by_id(schedule_id)
    assert schedule is not None
    return await _schedule_to_response(schedule, session)


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a schedule."""
    deleted = await ScheduleRepository(session).delete(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    get_scheduler_service().remove_schedule(schedule_id)
