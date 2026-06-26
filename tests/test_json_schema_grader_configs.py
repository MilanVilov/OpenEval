"""Tests for JSON schema grader config API validation."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import create_app

VALID_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
    },
    "required": ["answer"],
    "additionalProperties": False,
}

SAMPLE_CONFIG = {
    "name": "Schema Config",
    "system_prompt": "Return JSON.",
    "model": "gpt-4.1",
    "temperature": 0.0,
    "graders": [
        {
            "name": "shape",
            "type": "json_schema",
            "schema": VALID_SCHEMA,
            "threshold": 1.0,
        }
    ],
}


@pytest.fixture()
def app(tmp_path):
    """Create a fresh app instance backed by an in-memory SQLite DB."""
    with (
        patch("src.db.session.get_settings") as mock_db_settings,
        patch("src.app.get_settings") as mock_app_settings,
    ):
        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite://"
        settings.upload_dir = str(tmp_path / "uploads")
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
    """Ensure tables exist in the in-memory database."""
    from src.db.models import Base
    from src.db.session import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture()
async def client(app, _create_tables):
    """Yield an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_config_accepts_json_schema_grader(client: AsyncClient) -> None:
    """Configs can persist a JSON schema grader and return the stored schema."""
    response = await client.post("/api/configs", json=SAMPLE_CONFIG)

    assert response.status_code == 201
    payload = response.json()
    assert payload["graders"][0]["type"] == "json_schema"
    assert payload["graders"][0]["schema"] == VALID_SCHEMA


@pytest.mark.asyncio
async def test_create_config_rejects_json_schema_grader_without_schema(
    client: AsyncClient,
) -> None:
    """Configs reject schema graders that omit the required schema."""
    payload = {
        **SAMPLE_CONFIG,
        "graders": [{"name": "shape", "type": "json_schema"}],
    }

    response = await client.post("/api/configs", json=payload)

    assert response.status_code == 422
    assert "JSON schema graders require a schema" in response.text
