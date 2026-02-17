"""Tests for dataset and run CSV export endpoints."""

import csv
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from open_eval.app import create_app
from open_eval.db.models import Base
from open_eval.db.repositories import (
    ConfigRepository,
    DatasetRepository,
    ResultRepository,
    RunRepository,
)
from open_eval.db.session import get_engine, get_session_context


@pytest.fixture()
def app(tmp_path: Path):
    """Create an app backed by an in-memory SQLite database."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    with patch("open_eval.db.session.get_settings") as mock_db_settings, patch(
        "open_eval.config.get_settings"
    ) as mock_app_settings:
        settings = MagicMock()
        settings.database_url = "sqlite+aiosqlite://"
        settings.upload_dir = str(upload_dir)
        settings.cors_origins = ""
        mock_db_settings.return_value = settings
        mock_app_settings.return_value = settings

        import open_eval.db.session as session_mod

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
async def test_export_dataset_returns_csv_attachment(client: AsyncClient):
    """Dataset export returns the stored CSV file as an attachment."""
    response = await client.post(
        "/api/datasets",
        data={"name": "Support Tickets"},
        files={
            "file": (
                "tickets.csv",
                "input,expected_output\nhello,world\nbye,moon\n",
                "text/csv",
            )
        },
    )
    assert response.status_code == 201
    dataset_id = response.json()["id"]

    export_response = await client.get(f"/api/datasets/{dataset_id}/export")

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert 'filename="Support-Tickets.csv"' in export_response.headers["content-disposition"]
    assert "input,expected_output" in export_response.text
    assert "hello,world" in export_response.text


@pytest.mark.asyncio
async def test_export_run_returns_full_result_csv(client: AsyncClient, tmp_path: Path):
    """Run export includes grader reasoning, latency, tokens, and raw details."""
    dataset_path = tmp_path / "datasets" / "eval.csv"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text(
        "input,expected_output\nWhat is 2+2?,4\n",
        encoding="utf-8",
    )

    async with get_session_context() as session:
        config = await ConfigRepository(session).create(
            name="Math Grading",
            system_prompt="You are helpful.",
            model="gpt-4.1",
            comparer_type="exact_match",
        )
        dataset = await DatasetRepository(session).create(
            name="Arithmetic",
            file_path=str(dataset_path),
            row_count=1,
            columns=["input", "expected_output"],
        )
        run = await RunRepository(session).create(
            eval_config_id=config.id,
            dataset_id=dataset.id,
            total_rows=1,
        )
        await RunRepository(session).update_status(
            run.id,
            status="completed",
            summary={"accuracy": 1.0, "avg_latency_ms": 412},
        )
        await ResultRepository(session).create(
            eval_run_id=run.id,
            row_index=0,
            input_data="What is 2+2?",
            expected_output="4",
            actual_output="4",
            comparer_score=0.95,
            comparer_details={
                "llm_judge": {
                    "score": 0.95,
                    "passed": True,
                    "reasoning": "The answer matches exactly.",
                },
                "custom:clarity": {
                    "score": 0.9,
                    "passed": True,
                    "reasoning": "The response is short and clear.",
                    "model": "gpt-4.1-mini",
                },
            },
            passed=True,
            latency_ms=412,
            token_usage={"input_tokens": 25, "output_tokens": 7},
        )

    export_response = await client.get(f"/api/runs/{run.id}/export")
    rows = list(csv.DictReader(StringIO(export_response.text)))

    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert f'{run.id}.csv' in export_response.headers["content-disposition"]
    assert "run_id,run_status,config_name,dataset_name" in export_response.text
    assert len(rows) == 1
    assert rows[0]["grader_llm_judge_reasoning"] == "The answer matches exactly."
    assert rows[0]["grader_custom_clarity_reasoning"] == "The response is short and clear."
    assert rows[0]["latency_ms"] == "412"
    assert rows[0]["input_tokens"] == "25"
    assert rows[0]["output_tokens"] == "7"
    assert '"input_tokens": 25' in rows[0]["token_usage_json"]
