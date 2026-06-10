"""Tests for optional eval config comments."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import create_app

SAMPLE_CONFIG = {
    "name": "Commented Config",
    "comment": "Tracks the latest support prompt behavior.",
    "system_prompt": "You are a helpful assistant.",
    "model": "gpt-4.1",
    "temperature": 0.5,
    "graders": [
        {"name": "tone", "type": "prompt", "prompt": "Is the tone polite?", "threshold": 0.8}
    ],
}


@pytest.fixture()
def app():
    """Create a fresh app instance backed by an in-memory SQLite DB."""
    with patch("src.db.session.get_settings") as mock_settings:
        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite://"
        settings.upload_dir = "/tmp/openeval_test_uploads"
        settings.cors_origins = ""
        mock_settings.return_value = settings

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
async def test_create_config_with_comment(client: AsyncClient):
    """Creating a config stores and returns the optional comment."""
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG)

    assert resp.status_code == 201
    assert resp.json()["comment"] == "Tracks the latest support prompt behavior."


@pytest.mark.asyncio
async def test_create_config_without_comment_returns_null(client: AsyncClient):
    """Creating a config without a comment returns null."""
    payload = {k: v for k, v in SAMPLE_CONFIG.items() if k != "comment"}
    resp = await client.post("/api/configs", json=payload)

    assert resp.status_code == 201
    assert resp.json()["comment"] is None


@pytest.mark.asyncio
async def test_update_config_comment(client: AsyncClient):
    """Updating a config comment replaces the stored value."""
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG)
    config_id = resp.json()["id"]

    resp = await client.put(f"/api/configs/{config_id}", json={"comment": "Updated note"})

    assert resp.status_code == 200
    assert resp.json()["comment"] == "Updated note"


@pytest.mark.asyncio
async def test_update_config_blank_comment_clears_value(client: AsyncClient):
    """Sending a blank comment clears the stored value."""
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG)
    config_id = resp.json()["id"]

    resp = await client.put(f"/api/configs/{config_id}", json={"comment": "   "})

    assert resp.status_code == 200
    assert resp.json()["comment"] is None
