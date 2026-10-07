"""Round-trip Decisions configuration through the real JSON API and database."""

from collections.abc import AsyncIterator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from src.app import create_app
from src.config import Settings
from src.db.models import Base, Dataset
from src.db.session import get_session

QUESTIONS = [{"type": "predicate", "name": "relevant", "instructions": "Is it relevant?"}]
PAYLOAD = {
    "name": "Decisions test",
    "model": "gpt-6-luna",
    "system_prompt": "",
    "decision_config": {"questions": QUESTIONS},
    "graders": [{"name": "valid", "type": "json_schema", "schema": {"type": "object"}}],
}


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Provide the application API backed by isolated SQLite tables."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(
            Dataset(id="dataset", name="Test", file_path="unused.csv", row_count=1, columns=[])
        )
        await session.commit()
        with patch("src.app.get_settings", return_value=Settings(_env_file=None)):
            app = create_app()
        app.dependency_overrides[get_session] = lambda: session
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as api:
            yield api
    await engine.dispose()


async def test_decision_questions_survive_create_get_update_and_duplicate(
    client: AsyncClient,
) -> None:
    """All configuration workflows retain the named questions and settings."""
    created = await client.post("/api/configs", json=PAYLOAD)
    assert created.status_code == 201
    config_id = created.json()["id"]
    fetched = await client.get(f"/api/configs/{config_id}")
    assert fetched.json()["decision_config"] == {"questions": QUESTIONS}
    revised = [{**QUESTIONS[0], "name": "follow_up"}]
    updated = await client.put(
        f"/api/configs/{config_id}",
        json={
            "decision_config": {"questions": revised},
        },
    )
    assert updated.status_code == 200
    duplicate = await client.post(f"/api/configs/{config_id}/duplicate")
    assert duplicate.status_code == 201
    assert duplicate.json()["decision_config"] == {"questions": revised}


async def test_decision_model_cannot_lose_required_questions(client: AsyncClient) -> None:
    """Partial updates cannot clear questions while keeping the Decisions model."""
    created = await client.post("/api/configs", json=PAYLOAD)
    config_id = created.json()["id"]
    response = await client.put(f"/api/configs/{config_id}", json={"decision_config": None})
    assert response.status_code == 422
    fetched = await client.get(f"/api/configs/{config_id}")
    assert fetched.json()["decision_config"] == {"questions": QUESTIONS}


async def test_switch_between_decisions_and_responses(client: AsyncClient) -> None:
    """Changing API model requires consistent settings, without affecting ordinary configs."""
    created = await client.post("/api/configs", json=PAYLOAD)
    config_id = created.json()["id"]
    response = await client.put(
        f"/api/configs/{config_id}",
        json={
            "model": "gpt-4.1",
            "decision_config": None,
        },
    )
    assert response.status_code == 200
    response = await client.put(f"/api/configs/{config_id}", json={"model": "gpt-6-luna"})
    assert response.status_code == 422


async def test_invalid_question_configuration_returns_422(client: AsyncClient) -> None:
    """Malformed question schemas produce JSON validation errors."""
    response = await client.post(
        "/api/configs",
        json={
            **PAYLOAD,
            "decision_config": {"questions": [{"type": "choice"}]},
        },
    )
    assert response.status_code == 422


async def test_decision_runs_disable_flex_processing(client: AsyncClient) -> None:
    """Decisions runs are stored with accurate processing metadata."""
    created = await client.post("/api/configs", json=PAYLOAD)
    with patch("src.routers.runs.start_run_task"):
        response = await client.post(
            "/api/runs",
            json={
                "eval_config_id": created.json()["id"],
                "dataset_id": "dataset",
                "flex_enabled": True,
            },
        )
    assert response.status_code == 201
    assert response.json()["flex_enabled"] is False
