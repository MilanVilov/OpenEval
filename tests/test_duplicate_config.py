"""Tests for the POST /api/configs/{config_id}/duplicate endpoint."""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from open_eval.app import create_app

SAMPLE_CONFIG_PAYLOAD = {
    "name": "My Test Config",
    "system_prompt": "You are a helpful assistant.",
    "model": "gpt-4.1",
    "temperature": 0.5,
    "max_tokens": 1024,
    "tools": ["file_search"],
    "tool_options": {"vector_store_id": "vs_123"},
    "comparer_type": "exact_match",
    "comparer_config": {},
    "custom_graders": [
        {"name": "tone", "prompt": "Is the tone polite?", "threshold": 0.8}
    ],
    "concurrency": 3,
    "reasoning_config": {"effort": "high"},
    "response_format": {"type": "text"},
}


@pytest.fixture()
def app():
    """Create a fresh app instance backed by an in-memory SQLite DB."""
    with patch("open_eval.db.session.get_settings") as mock_settings:
        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite://"
        settings.upload_dir = "/tmp/openeval_test_uploads"
        settings.cors_origins = ""
        mock_settings.return_value = settings

        # Reset module-level singletons so the in-memory DB is used
        import open_eval.db.session as session_mod

        session_mod._engine = None
        session_mod._session_factory = None

        application = create_app()
        yield application

        session_mod._engine = None
        session_mod._session_factory = None


@pytest.fixture()
async def _create_tables(app):
    """Ensure tables exist in the in-memory database."""
    from open_eval.db.session import get_engine
    from open_eval.db.models import Base

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
async def test_duplicate_config_creates_copy_with_new_id(client: AsyncClient):
    """Duplicating a config creates a new config with ' copy' suffix and same fields."""
    # Create the original config
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG_PAYLOAD)
    assert resp.status_code == 201
    original = resp.json()

    # Duplicate it
    resp = await client.post(f"/api/configs/{original['id']}/duplicate")
    assert resp.status_code == 201
    copy = resp.json()

    # Different id
    assert copy["id"] != original["id"]

    # Name has ' copy' appended
    assert copy["name"] == f"{original['name']} copy"

    # All other fields match the original
    for field in [
        "system_prompt",
        "model",
        "temperature",
        "max_tokens",
        "tools",
        "tool_options",
        "comparer_type",
        "comparer_config",
        "concurrency",
        "reasoning_config",
        "response_format",
    ]:
        assert copy[field] == original[field], f"Mismatch on {field}"

    # Custom graders match (without 'model' key since it was omitted in schema)
    assert len(copy["custom_graders"]) == len(original["custom_graders"])
    assert copy["custom_graders"][0]["name"] == "tone"


@pytest.mark.asyncio
async def test_duplicate_config_not_found(client: AsyncClient):
    """Attempting to duplicate a nonexistent config returns 404."""
    resp = await client.post("/api/configs/nonexistent_id/duplicate")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Configuration not found"


@pytest.mark.asyncio
async def test_duplicate_config_appears_in_list(client: AsyncClient):
    """After duplicating, both original and copy appear in the config list."""
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG_PAYLOAD)
    assert resp.status_code == 201
    original = resp.json()

    await client.post(f"/api/configs/{original['id']}/duplicate")

    resp = await client.get("/api/configs")
    assert resp.status_code == 200
    configs = resp.json()
    names = [c["name"] for c in configs]
    assert "My Test Config" in names
    assert "My Test Config copy" in names
