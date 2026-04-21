"""Tests for scheduled runs + Slack notification plumbing."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import create_app

SAMPLE_CONFIG_PAYLOAD = {
    "name": "Sched Config",
    "system_prompt": "You are helpful.",
    "model": "gpt-4.1",
    "temperature": 0.5,
    "max_tokens": 512,
    "tools": [],
    "tool_options": {},
    "comparer_type": "exact_match",
    "comparer_config": {},
    "custom_graders": [],
    "concurrency": 2,
    "reasoning_config": None,
    "response_format": {"type": "text"},
}


@pytest.fixture()
def app():
    """Fresh app against an in-memory SQLite database."""
    import src.config as config_mod
    import src.db.session as session_mod

    config_mod.get_settings.cache_clear()

    with (
        patch("src.config.get_settings") as mock_config_settings,
        patch("src.db.session.get_settings") as mock_session_settings,
    ):
        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite://"
        settings.upload_dir = "/tmp/openeval_test_uploads"
        settings.cors_origins = ""
        settings.slack_webhook_url = ""
        settings.app_base_url = ""
        mock_config_settings.return_value = settings
        mock_session_settings.return_value = settings

        session_mod._engine = None
        session_mod._session_factory = None

        application = create_app()
        yield application

        session_mod._engine = None
        session_mod._session_factory = None
        config_mod.get_settings.cache_clear()


@pytest.fixture()
async def _create_tables(app):
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
    # Patch the scheduler so jobs don't actually register / fire during tests.
    with patch("src.routers.schedules.get_scheduler_service") as get_sched:
        mock_scheduler = MagicMock()
        mock_scheduler.get_next_run_at.return_value = None
        get_sched.return_value = mock_scheduler
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


async def _create_dataset(client: AsyncClient) -> str:
    csv_body = b"input,expected_output\nhi,hello\n"
    files = {"file": ("sample.csv", csv_body, "text/csv")}
    data = {"name": "Sched Dataset", "input_field": "input"}
    resp = await client.post("/api/datasets", data=data, files=files)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


async def _create_config(client: AsyncClient) -> str:
    resp = await client.post("/api/configs", json=SAMPLE_CONFIG_PAYLOAD)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Unit tests — cron validation
# ---------------------------------------------------------------------------


def test_is_valid_cron_accepts_standard_expressions() -> None:
    from src.services.scheduler import is_valid_cron

    assert is_valid_cron("0 9 * * *")
    assert is_valid_cron("*/15 * * * *")
    assert is_valid_cron("0 9 * * 1,3,5")


def test_is_valid_cron_rejects_bad_input() -> None:
    from src.services.scheduler import is_valid_cron

    assert not is_valid_cron("")
    assert not is_valid_cron("not a cron")
    assert not is_valid_cron("99 * * * *")
    assert not is_valid_cron("0 0 9 * * *")


def test_is_allowed_webhook_url_rejects_non_slack_hosts() -> None:
    from src.services.slack_notifier import is_allowed_webhook_url

    assert is_allowed_webhook_url("https://hooks.slack.com/services/test")
    assert not is_allowed_webhook_url("http://hooks.slack.com/services/test")
    assert not is_allowed_webhook_url("https://example.com/services/test")


# ---------------------------------------------------------------------------
# Unit tests — Slack block builder
# ---------------------------------------------------------------------------


def _fake_run(**summary: object) -> SimpleNamespace:
    return SimpleNamespace(
        id="run_abc",
        summary=dict(summary),
        config=SimpleNamespace(name="Cfg"),
        dataset=SimpleNamespace(name="DS"),
    )


def test_build_blocks_without_previous_run() -> None:
    from src.services.slack_notifier import build_blocks

    run = _fake_run(accuracy=0.8, avg_score=0.9, avg_latency_ms=1200,
                    passed=8, failed=2, errors=0)
    schedule = SimpleNamespace(name="Nightly", min_accuracy=None)
    blocks = build_blocks(run=run, schedule=schedule, previous_run=None)
    assert blocks[0]["type"] == "header"
    assert "Nightly" in blocks[0]["text"]["text"]
    # Header uses the success emoji when no threshold is violated.
    assert "✅" in blocks[0]["text"]["text"]


def test_build_blocks_flags_below_threshold() -> None:
    from src.services.slack_notifier import build_blocks

    run = _fake_run(accuracy=0.5, avg_score=0.5, avg_latency_ms=1000,
                    passed=5, failed=5, errors=0)
    schedule = SimpleNamespace(name="Nightly", min_accuracy=0.9)
    blocks = build_blocks(run=run, schedule=schedule, previous_run=None)
    assert "🚨" in blocks[0]["text"]["text"]
    # Context block should mention the threshold warning.
    joined = " ".join(
        b["text"]["text"] for b in blocks if b.get("type") == "section" and "text" in b
    )
    assert "below threshold" in joined


def test_build_blocks_renders_delta_against_previous_run() -> None:
    from src.services.slack_notifier import build_blocks

    run = _fake_run(accuracy=0.9, avg_score=0.9, avg_latency_ms=800,
                    passed=9, failed=1, errors=0)
    prev = _fake_run(accuracy=0.7, avg_score=0.7, avg_latency_ms=1200,
                     passed=7, failed=3, errors=0)
    schedule = SimpleNamespace(name="Nightly", min_accuracy=None)
    blocks = build_blocks(run=run, schedule=schedule, previous_run=prev)
    fields_block = next(b for b in blocks if b.get("type") == "section" and "fields" in b)
    rendered = " ".join(f["text"] for f in fields_block["fields"])
    # Accuracy up, latency down — must contain arrow symbols.
    assert "▲" in rendered or "▼" in rendered


# ---------------------------------------------------------------------------
# Router integration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_schedule_rejects_invalid_cron(client: AsyncClient) -> None:
    config_id = await _create_config(client)
    dataset_id = await _create_dataset(client)
    resp = await client.post("/api/schedules", json={
        "name": "bad",
        "eval_config_id": config_id,
        "dataset_id": dataset_id,
        "cron_expression": "not a cron",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_schedule_crud_and_toggle(client: AsyncClient) -> None:
    config_id = await _create_config(client)
    dataset_id = await _create_dataset(client)

    # Create
    resp = await client.post("/api/schedules", json={
        "name": "Nightly",
        "eval_config_id": config_id,
        "dataset_id": dataset_id,
        "cron_expression": "0 9 * * *",
        "slack_webhook_url": "https://hooks.slack.com/services/test",
        "min_accuracy": 0.8,
    })
    assert resp.status_code == 201, resp.text
    schedule = resp.json()
    assert schedule["enabled"] is True
    assert schedule["config_name"] == "Sched Config"
    assert schedule["dataset_name"] == "Sched Dataset"
    assert schedule["slack_webhook_url"] is None
    assert schedule["has_slack_webhook"] is True
    sid = schedule["id"]

    # List
    resp = await client.get("/api/schedules")
    assert resp.status_code == 200
    assert any(s["id"] == sid for s in resp.json())

    # Patch — update cron and accuracy
    resp = await client.patch(f"/api/schedules/{sid}", json={
        "cron_expression": "0 10 * * *",
        "min_accuracy": 0.9,
    })
    assert resp.status_code == 200
    assert resp.json()["cron_expression"] == "0 10 * * *"
    assert resp.json()["min_accuracy"] == 0.9

    # Patch with invalid cron → 422
    resp = await client.patch(f"/api/schedules/{sid}", json={"cron_expression": "bad"})
    assert resp.status_code == 422

    resp = await client.patch(f"/api/schedules/{sid}", json={
        "slack_webhook_url": "https://example.com/not-slack",
    })
    assert resp.status_code == 422

    resp = await client.patch(f"/api/schedules/{sid}", json={
        "slack_webhook_url": None,
    })
    assert resp.status_code == 200
    assert resp.json()["slack_webhook_url"] is None
    assert resp.json()["has_slack_webhook"] is False

    # Toggle off
    resp = await client.post(f"/api/schedules/{sid}/toggle")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    # Delete
    resp = await client.delete(f"/api/schedules/{sid}")
    assert resp.status_code == 204
    resp = await client.get(f"/api/schedules/{sid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_now_creates_scheduled_run(client: AsyncClient) -> None:
    config_id = await _create_config(client)
    dataset_id = await _create_dataset(client)

    resp = await client.post("/api/schedules", json={
        "name": "Trigger me",
        "eval_config_id": config_id,
        "dataset_id": dataset_id,
        "cron_expression": "0 9 * * *",
    })
    assert resp.status_code == 201
    sid = resp.json()["id"]

    # Patch out run_evaluation so we don't actually hit OpenAI.
    with patch("src.routers.schedules.run_evaluation", AsyncMock(return_value=None)):
        resp = await client.post(f"/api/schedules/{sid}/run-now")
        assert resp.status_code == 200

    # A new run should now exist for this config/dataset.
    resp = await client.get("/api/runs")
    assert resp.status_code == 200
    runs = resp.json()
    assert len(runs) >= 1
    assert runs[0]["eval_config_id"] == config_id
    assert runs[0]["dataset_id"] == dataset_id


@pytest.mark.asyncio
async def test_update_schedule_returns_schedule_not_found_before_ref_checks(
    client: AsyncClient,
) -> None:
    resp = await client.patch("/api/schedules/missing", json={
        "eval_config_id": "missing-config",
    })

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Schedule not found"
