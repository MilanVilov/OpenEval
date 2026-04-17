"""Tests for config tags: create, update, duplicate, and GET /api/configs/tags."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import create_app

SAMPLE_CONFIG = {
    "name": "Tagged Config",
    "system_prompt": "You are a helpful assistant.",
    "model": "gpt-4.1",
    "temperature": 0.5,
    "tags": ["production", "v2"],
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
    from src.db.session import get_engine
    from src.db.models import Base

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
async def test_create_config_with_tags(client: AsyncClient):
    """Creating a config with tags stores and returns them."""
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG)
    assert resp.status_code == 201
    data = resp.json()
    assert data["tags"] == ["production", "v2"]


@pytest.mark.asyncio
async def test_create_config_without_tags_returns_empty_list(client: AsyncClient):
    """Creating a config without tags returns an empty list."""
    payload = {k: v for k, v in SAMPLE_CONFIG.items() if k != "tags"}
    resp = await client.post("/api/configs", json=payload)
    assert resp.status_code == 201
    assert resp.json()["tags"] == []


@pytest.mark.asyncio
async def test_update_config_tags(client: AsyncClient):
    """Updating tags on a config replaces the tag list."""
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG)
    config_id = resp.json()["id"]

    resp = await client.put(f"/api/configs/{config_id}", json={"tags": ["staging"]})
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["staging"]


@pytest.mark.asyncio
async def test_update_config_remove_all_tags(client: AsyncClient):
    """Setting tags to an empty list removes all tags."""
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG)
    config_id = resp.json()["id"]

    resp = await client.put(f"/api/configs/{config_id}", json={"tags": []})
    assert resp.status_code == 200
    assert resp.json()["tags"] == []


@pytest.mark.asyncio
async def test_duplicate_config_preserves_tags(client: AsyncClient):
    """Duplicating a config copies its tags."""
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG)
    config_id = resp.json()["id"]

    resp = await client.post(f"/api/configs/{config_id}/duplicate")
    assert resp.status_code == 201
    copy = resp.json()
    assert copy["tags"] == ["production", "v2"]
    assert copy["id"] != config_id


@pytest.mark.asyncio
async def test_list_tags_returns_deduplicated_sorted(client: AsyncClient):
    """GET /api/configs/tags returns a deduplicated, sorted list of all tags."""
    await client.post("/api/configs", json={**SAMPLE_CONFIG, "tags": ["beta", "v2"]})
    await client.post("/api/configs", json={**SAMPLE_CONFIG, "name": "Config B", "tags": ["alpha", "v2"]})
    await client.post("/api/configs", json={**SAMPLE_CONFIG, "name": "Config C", "tags": []})

    resp = await client.get("/api/configs/tags")
    assert resp.status_code == 200
    assert resp.json() == ["alpha", "beta", "v2"]


@pytest.mark.asyncio
async def test_list_tags_empty_when_no_configs(client: AsyncClient):
    """GET /api/configs/tags returns an empty list when no configs exist."""
    resp = await client.get("/api/configs/tags")
    assert resp.status_code == 200
    assert resp.json() == []
