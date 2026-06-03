"""Tests for paginated list endpoints with search filters."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import create_app
from src.db.models import Base
from src.db.repositories import ConfigRepository, DatasetRepository, RunRepository
from src.db.session import get_engine, get_session_context


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
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_list_configs_paginates_and_searches_with_tags(client: AsyncClient):
    """Config list supports pagination, search, and selected tags together."""
    async with get_session_context() as session:
        repo = ConfigRepository(session)
        await repo.create(
            name="Alpha Draft",
            system_prompt="Draft support checks",
            model="gpt-4.1",
            tags=["draft"],
        )
        await repo.create(
            name="Alpha Production",
            system_prompt="Production support checks",
            model="gpt-4.1",
            tags=["prod"],
        )
        for index in range(11):
            await repo.create(
                name=f"Archive Config {index}",
                system_prompt="Old prompt",
                model="gpt-4.1",
            )

    full_response = await client.get("/api/configs")
    assert full_response.status_code == 200
    assert isinstance(full_response.json(), list)
    assert len(full_response.json()) == 13

    page_response = await client.get("/api/configs?page=1&page_size=10")
    assert page_response.status_code == 200
    page = page_response.json()
    assert page["total"] == 13
    assert len(page["items"]) == 10
    assert page["page_size"] == 10

    search_response = await client.get("/api/configs?page=1&page_size=10&search=alpha&tags=prod")
    assert search_response.status_code == 200
    filtered = search_response.json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["name"] == "Alpha Production"


@pytest.mark.asyncio
async def test_list_datasets_paginates_and_searches(client: AsyncClient, tmp_path: Path):
    """Dataset list returns filtered pages without loading every dataset."""
    async with get_session_context() as session:
        repo = DatasetRepository(session)
        for index in range(12):
            await repo.create(
                name=f"Dataset {index}",
                file_path=str(tmp_path / f"dataset-{index}.csv"),
                row_count=index + 1,
                columns=["input", "expected_output"],
            )
        await repo.create(
            name="Support Tickets",
            file_path=str(tmp_path / "support.csv"),
            row_count=2,
            columns=["input", "expected_output"],
        )

    response = await client.get("/api/datasets?page=1&page_size=5&search=support")

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 1
    assert page["pages"] == 1
    assert page["items"][0]["name"] == "Support Tickets"


@pytest.mark.asyncio
async def test_list_runs_paginates_and_searches_related_names(client: AsyncClient, tmp_path: Path):
    """Run list search matches config and dataset names while paginating."""
    async with get_session_context() as session:
        config_repo = ConfigRepository(session)
        dataset_repo = DatasetRepository(session)
        run_repo = RunRepository(session)
        support_config = await config_repo.create(
            name="Support Eval",
            system_prompt="Support prompt",
            model="gpt-4.1",
        )
        billing_config = await config_repo.create(
            name="Billing Eval",
            system_prompt="Billing prompt",
            model="gpt-4.1",
        )
        support_dataset = await dataset_repo.create(
            name="Support Tickets",
            file_path=str(tmp_path / "support.csv"),
            row_count=2,
            columns=["input", "expected_output"],
        )
        billing_dataset = await dataset_repo.create(
            name="Billing Tickets",
            file_path=str(tmp_path / "billing.csv"),
            row_count=2,
            columns=["input", "expected_output"],
        )
        await run_repo.create(
            eval_config_id=support_config.id,
            dataset_id=support_dataset.id,
            total_rows=2,
        )
        await run_repo.create(
            eval_config_id=billing_config.id,
            dataset_id=billing_dataset.id,
            total_rows=2,
        )

    response = await client.get("/api/runs?page=1&page_size=10&search=support")

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 1
    assert page["items"][0]["config_name"] == "Support Eval"
    assert page["items"][0]["dataset_name"] == "Support Tickets"
