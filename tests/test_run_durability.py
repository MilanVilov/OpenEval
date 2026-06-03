"""Integration tests for durable run persistence and stale-run recovery."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import create_app
from src.db.models import Base, EvalResult
from src.db.repositories import (
    ConfigRepository,
    DatasetRepository,
    ResultRepository,
    RunRepository,
)
from src.db.session import get_engine, get_session_context
from src.services.run_monitor import RUN_HEARTBEAT_TIMEOUT, STALE_RUN_ERROR_MESSAGE


@pytest.fixture()
def app(tmp_path: Path):
    """Create an app backed by an in-memory SQLite database."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    with patch("src.db.session.get_settings") as mock_db_settings, patch(
        "src.config.get_settings"
    ) as mock_app_settings:
        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite://"
        settings.upload_dir = str(upload_dir)
        settings.cors_origins = ""
        settings.app_base_url = ""
        mock_db_settings.return_value = settings
        mock_app_settings.return_value = settings

        import src.db.session as session_mod

        session_mod._engine = None
        session_mod._session_factory = None

        application = create_app()
        yield application

        session_mod._engine = None
        session_mod._session_factory = None


@pytest.fixture()
async def _create_tables(app):
    """Create database tables for the test app."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture()
async def client(app, _create_tables):
    """Yield an async HTTP client for API tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _create_run_fixture() -> tuple[str, str, str]:
    """Insert a config, dataset, and run for durability tests."""
    async with get_session_context() as session:
        config = await ConfigRepository(session).create(
            name="Config",
            system_prompt="Prompt",
            model="gpt-4.1",
            temperature=0.0,
        )
        dataset = await DatasetRepository(session).create(
            name="Dataset",
            file_path="/tmp/dataset.csv",
            row_count=1,
            columns=["input", "expected_output"],
            csv_content="input,expected_output\nhello,world\n",
        )
        run = await RunRepository(session).create(
            eval_config_id=config.id,
            dataset_id=dataset.id,
            total_rows=1,
        )
        return config.id, dataset.id, run.id


@pytest.mark.asyncio
async def test_result_repository_upsert_batch_replaces_existing_row(_create_tables):
    """Upserted results should replace an existing row instead of duplicating it."""
    _config_id, _dataset_id, run_id = await _create_run_fixture()

    first_result = EvalResult(
        eval_run_id=run_id,
        row_index=0,
        input_data="hello",
        expected_output="world",
        actual_output="first",
        comparer_score=0.0,
        passed=False,
    )
    second_result = EvalResult(
        eval_run_id=run_id,
        row_index=0,
        input_data="hello",
        expected_output="world",
        actual_output="second",
        comparer_score=1.0,
        passed=True,
    )

    async with get_session_context() as session:
        result_repo = ResultRepository(session)
        await result_repo.upsert_batch([first_result])
        await result_repo.upsert_batch([second_result])
        rows = await result_repo.list_by_run(run_id)

    assert len(rows) == 1
    assert rows[0].actual_output == "second"
    assert rows[0].comparer_score == 1.0
    assert rows[0].passed is True


@pytest.mark.asyncio
async def test_progress_endpoint_marks_stale_run_failed(client: AsyncClient):
    """Polling progress should fail stale active runs instead of leaving them stuck."""
    _config_id, _dataset_id, run_id = await _create_run_fixture()
    stale_time = datetime.now(UTC) - RUN_HEARTBEAT_TIMEOUT - RUN_HEARTBEAT_TIMEOUT

    async with get_session_context() as session:
        await RunRepository(session).update_status(
            run_id,
            status="running",
            progress=4,
            total_rows=10,
            heartbeat_at=stale_time,
            started_at=stale_time,
        )

    response = await client.get(f"/api/runs/{run_id}/progress")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_message"] == STALE_RUN_ERROR_MESSAGE

    async with get_session_context() as session:
        stored_run = await RunRepository(session).get_by_id(run_id)

    assert stored_run is not None
    assert stored_run.status == "failed"
    assert stored_run.error_message == STALE_RUN_ERROR_MESSAGE
