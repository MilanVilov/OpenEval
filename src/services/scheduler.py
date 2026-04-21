"""In-process APScheduler service — fires scheduled evaluation runs.

Jobs are rehydrated from the ``schedules`` table on startup. Mutations in
``/api/schedules`` call :meth:`SchedulerService.sync_schedule` to add, replace,
or remove the matching APScheduler job.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.db.models import Schedule
from src.db.repositories import (
    ConfigRepository,
    DatasetRepository,
    RunRepository,
    ScheduleRepository,
)
from src.db.session import get_session_context
from src.services.eval_runner import run_evaluation

logger = logging.getLogger(__name__)


def is_valid_cron(expression: str) -> bool:
    """Return ``True`` if ``expression`` is a valid 5-field cron expression."""
    expression = (expression or "").strip()
    if not expression:
        return False
    if len(expression.split()) != 5:
        return False
    try:
        CronTrigger.from_crontab(expression, timezone="UTC")
    except ValueError:
        return False
    return True


class SchedulerService:
    """Thin wrapper around :class:`AsyncIOScheduler` driven by DB rows."""

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None

    async def start(self) -> None:
        """Start the scheduler and load enabled schedules from the database."""
        if self._scheduler is not None:
            return
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._scheduler.start()
        await self._rehydrate()

    async def shutdown(self) -> None:
        """Stop the scheduler cleanly."""
        if self._scheduler is None:
            return
        self._scheduler.shutdown(wait=False)
        self._scheduler = None

    async def _rehydrate(self) -> None:
        """Load enabled schedules and register their cron jobs.

        If the ``schedules`` table is missing (e.g. migrations have not run
        against this database yet), log a warning and keep the app running
        without any scheduled jobs rather than failing startup.
        """
        try:
            async with get_session_context() as session:
                schedules = await ScheduleRepository(session).list_enabled()
        except Exception as exc:  # noqa: BLE001 — never block startup
            logger.warning(
                "Scheduler rehydrate skipped: %s. "
                "Run `alembic upgrade head` to enable scheduled runs.",
                exc,
            )
            return
        for schedule in schedules:
            self._register(schedule)

    def sync_schedule(self, schedule: Schedule) -> None:
        """Add, replace, or remove the APScheduler job for a schedule row."""
        if self._scheduler is None:
            return
        job_id = schedule.id
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        if schedule.enabled:
            self._register(schedule)

    def remove_schedule(self, schedule_id: str) -> None:
        """Remove any scheduled job for ``schedule_id``."""
        if self._scheduler is None:
            return
        if self._scheduler.get_job(schedule_id):
            self._scheduler.remove_job(schedule_id)

    def get_next_run_at(self, schedule: Schedule) -> datetime | None:
        """Return the next fire time for an enabled schedule, or ``None``."""
        if self._scheduler is None or not schedule.enabled:
            return None
        job = self._scheduler.get_job(schedule.id)
        return job.next_run_time if job else None

    def _register(self, schedule: Schedule) -> None:
        """Internal: register a job that calls :func:`_trigger_run`."""
        assert self._scheduler is not None  # invariant: only called after start()
        try:
            trigger = CronTrigger.from_crontab(schedule.cron_expression, timezone="UTC")
        except ValueError as exc:
            logger.error(
                "Schedule %s has invalid cron %r: %s",
                schedule.id,
                schedule.cron_expression,
                exc,
            )
            return
        self._scheduler.add_job(
            _trigger_run,
            trigger=trigger,
            args=[schedule.id],
            id=schedule.id,
            replace_existing=True,
            misfire_grace_time=60,
            coalesce=True,
        )


async def _trigger_run(schedule_id: str) -> None:
    """Create a new :class:`EvalRun` for a schedule and execute it.

    Opens its own DB session; this runs outside any HTTP request context.
    """
    async with get_session_context() as session:
        schedule = await ScheduleRepository(session).get_by_id(schedule_id)
        if schedule is None or not schedule.enabled:
            return
        dataset = await DatasetRepository(session).get_by_id(schedule.dataset_id)
        config = await ConfigRepository(session).get_by_id(schedule.eval_config_id)
        if dataset is None or config is None:
            logger.warning(
                "Schedule %s skipped: missing config or dataset", schedule_id,
            )
            return
        run = await RunRepository(session).create(
            eval_config_id=schedule.eval_config_id,
            dataset_id=schedule.dataset_id,
            total_rows=dataset.row_count,
            scheduled_by_id=schedule.id,
        )
        await ScheduleRepository(session).mark_triggered(
            schedule.id, when=datetime.now(UTC),
        )
        run_id = run.id

    asyncio.create_task(run_evaluation(run_id))


# Process-wide singleton accessor -------------------------------------------

_scheduler_service: SchedulerService | None = None


def get_scheduler_service() -> SchedulerService:
    """Return the process-wide :class:`SchedulerService` instance."""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
