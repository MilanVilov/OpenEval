"""Run monitoring helpers for stale heartbeat detection."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories import RunRepository

RUN_HEARTBEAT_TIMEOUT = timedelta(minutes=30)
STALE_RUN_ERROR_MESSAGE = (
    "Run heartbeat expired before completion. Partial results were saved."
)


async def fail_stale_run(session: AsyncSession, run_id: str) -> bool:
    """Mark one run failed when its heartbeat is older than the timeout."""
    run_repo = RunRepository(session)
    now = _current_time()
    return await run_repo.fail_stale_run(
        run_id,
        stale_before=now - RUN_HEARTBEAT_TIMEOUT,
        error_message=STALE_RUN_ERROR_MESSAGE,
        completed_at=now,
    )


async def fail_stale_runs(session: AsyncSession) -> int:
    """Mark every stale active run failed and return the number of updates."""
    run_repo = RunRepository(session)
    now = _current_time()
    return await run_repo.fail_stale_active_runs(
        stale_before=now - RUN_HEARTBEAT_TIMEOUT,
        error_message=STALE_RUN_ERROR_MESSAGE,
        completed_at=now,
    )


def _current_time() -> datetime:
    """Return a naive UTC timestamp matching the database datetime columns."""
    return datetime.now(UTC).replace(tzinfo=None)
