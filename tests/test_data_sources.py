"""Integration tests for remote data source and dataset import APIs."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient

from src.app import create_app
from src.db.models import Base
from src.db.session import get_engine


@pytest.fixture()
def app(tmp_path: Path):
    """Create an app backed by an in-memory SQLite database."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    settings = SimpleNamespace(
        database_url="sqlite+aiosqlite://",
        upload_dir=str(upload_dir),
        cors_origins="",
        data_source_encryption_key=Fernet.generate_key().decode("utf-8"),
    )

    with (
        patch("src.db.session.get_settings", return_value=settings),
        patch("src.config.get_settings", return_value=settings),
        patch("src.services.data_source_crypto.get_settings", return_value=settings),
        patch("src.services.dataset_imports.get_settings", return_value=settings),
    ):
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


async def _create_source(client: AsyncClient) -> str:
    """Create a reusable page-based data source for tests."""
    response = await client.post(
        "/api/data-sources",
        json={
            "name": "Remote Tickets",
            "url": "https://example.test/tickets",
            "method": "GET",
            "auth_type": "bearer",
            "query_params": {"scope": "all"},
            "headers": {"X-Public": "visible"},
            "bearer_token": "top-secret",
            "secret_headers": {"X-Api-Key": "hidden"},
            "pagination_mode": "page",
            "pagination_config": {
                "page_param": "page",
                "page_size_param": "limit",
                "page_size": 2,
                "has_more_path": "$.meta.has_more",
            },
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_preset(client: AsyncClient, source_id: str) -> str:
    """Create a mapping preset for the test data source."""
    response = await client.post(
        f"/api/data-sources/{source_id}/presets",
        json={
            "name": "Ticket Mapping",
            "records_path": "$.items",
            "field_mapping": {
                "input": "question",
                "expected_output": "answer",
                "category": "kind",
            },
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_data_source_crud_redacts_secrets_and_enforces_delete_conflicts(
    client: AsyncClient,
) -> None:
    """Source detail should redact secrets and source deletion should respect preset references."""
    source_id = await _create_source(client)

    detail = await client.get(f"/api/data-sources/{source_id}")
    assert detail.status_code == 200
    assert detail.json()["has_secret_credentials"] is True
    assert detail.json()["secret_header_names"] == ["X-Api-Key"]
    assert "bearer_token" not in detail.text
    assert detail.json()["headers"] == {"X-Public": "visible"}

    await _create_preset(client, source_id)

    delete_while_referenced = await client.delete(f"/api/data-sources/{source_id}")
    assert delete_while_referenced.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_data_source_copies_connection_and_saved_mappings(
    client: AsyncClient,
) -> None:
    """Duplicating a data source should copy its request config, secrets, and presets."""
    source_id = await _create_source(client)
    await _create_preset(client, source_id)

    duplicate_response = await client.post(f"/api/data-sources/{source_id}/duplicate")
    assert duplicate_response.status_code == 201
    duplicate = duplicate_response.json()
    assert duplicate["id"] != source_id
    assert duplicate["name"] == "Remote Tickets copy"
    assert duplicate["has_secret_credentials"] is True
    assert duplicate["secret_header_names"] == ["X-Api-Key"]

    duplicate_detail = await client.get(f"/api/data-sources/{duplicate['id']}")
    assert duplicate_detail.status_code == 200
    detail_body = duplicate_detail.json()
    assert detail_body["url"] == "https://example.test/tickets"
    assert detail_body["method"] == "GET"
    assert detail_body["auth_type"] == "bearer"
    assert detail_body["query_params"] == {"scope": "all"}
    assert detail_body["headers"] == {"X-Public": "visible"}
    assert detail_body["pagination_mode"] == "page"
    assert detail_body["pagination_config"] == {
        "page_param": "page",
        "page_size_param": "limit",
        "page_size": 2,
        "has_more_path": "$.meta.has_more",
    }

    duplicate_presets = await client.get(f"/api/data-sources/{duplicate['id']}/presets")
    assert duplicate_presets.status_code == 200
    duplicate_presets_body = duplicate_presets.json()
    assert len(duplicate_presets_body) == 1
    assert duplicate_presets_body[0]["data_source_id"] == duplicate["id"]
    assert duplicate_presets_body[0]["name"] == "Ticket Mapping"
    assert duplicate_presets_body[0]["records_path"] == "$.items"
    assert duplicate_presets_body[0]["field_mapping"] == {
        "input": "question",
        "expected_output": "answer",
        "category": "kind",
    }


@pytest.mark.asyncio
async def test_duplicate_data_source_not_found_returns_404(
    client: AsyncClient,
) -> None:
    """Duplicating a missing data source should return 404."""
    response = await client.post("/api/data-sources/missing/duplicate")
    assert response.status_code == 404
    assert response.json() == {"detail": "Data source not found"}


@pytest.mark.asyncio
async def test_import_preset_crud_round_trip(
    client: AsyncClient,
) -> None:
    """Presets should support create, list, get, update, and delete for one source."""
    source_id = await _create_source(client)

    create_response = await client.post(
        f"/api/data-sources/{source_id}/presets",
        json={
            "name": "Draft Mapping",
            "records_path": "$.recipes",
            "field_mapping": {
                "input": "name",
                "expected_output": "instructions[0]",
            },
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    preset_id = created["id"]
    assert created["data_source_id"] == source_id
    assert created["records_path"] == "$.recipes"

    list_response = await client.get(f"/api/data-sources/{source_id}/presets")
    assert list_response.status_code == 200
    assert [preset["id"] for preset in list_response.json()] == [preset_id]

    detail_response = await client.get(f"/api/data-sources/{source_id}/presets/{preset_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["field_mapping"] == {
        "input": "name",
        "expected_output": "instructions[0]",
    }

    update_response = await client.put(
        f"/api/data-sources/{source_id}/presets/{preset_id}",
        json={
            "name": "Draft Mapping Updated",
            "field_mapping": {
                "input": "Recipe: {name}",
                "expected_output": "{instructions[0]}",
            },
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Draft Mapping Updated"
    assert updated["field_mapping"] == {
        "input": "Recipe: {name}",
        "expected_output": "{instructions[0]}",
    }

    delete_response = await client.delete(f"/api/data-sources/{source_id}/presets/{preset_id}")
    assert delete_response.status_code == 204

    empty_list_response = await client.get(f"/api/data-sources/{source_id}/presets")
    assert empty_list_response.status_code == 200
    assert empty_list_response.json() == []


@pytest.mark.asyncio
async def test_explore_data_source_supports_inline_mapping_without_preset(
    client: AsyncClient,
) -> None:
    """Explore should preview mapped rows from a draft records path and mapping."""
    source_id = await _create_source(client)

    async def fake_request_json(data_source, *, request_params, request_body):
        return {
            "recipes": [
                {
                    "name": "Mango Salsa Chicken",
                    "difficulty": "Easy",
                    "instructions": ["Season chicken", "Serve over rice"],
                }
            ],
            "total": 1,
            "skip": 0,
            "limit": 30,
        }

    with patch("src.services.remote_data_sources._request_json", new=fake_request_json):
        response = await client.post(
            f"/api/data-sources/{source_id}/explore",
            json={
                "records_path": "$.recipes",
                "field_mapping": {
                    "input": "Recipe: {name}",
                    "expected_output": '{difficulty == "Easy" ? instructions[0] : "Skip"}',
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert "$.recipes" in body["candidate_array_paths"]
    assert "instructions[]" in body["field_candidates"]
    assert body["mapped_rows"] == [
        {
            "input": "Recipe: Mango Salsa Chicken",
            "expected_output": "Season chicken",
        }
    ]


@pytest.mark.asyncio
async def test_explore_data_source_returns_mapped_rows_and_page_states(
    client: AsyncClient,
) -> None:
    """Explore should fetch, map, and paginate remote records."""
    source_id = await _create_source(client)
    preset_id = await _create_preset(client, source_id)
    calls: list[dict[str, object]] = []

    async def fake_request_json(data_source, *, request_params, request_body):
        calls.append({"url": data_source.url, "params": request_params, "body": request_body})
        page = int(request_params.get("page", 1))
        return (
            {
                "items": [
                    {"question": "q1", "answer": "a1", "kind": "alpha"},
                    {"question": "q2", "answer": "a2", "kind": "beta"},
                ],
                "meta": {"has_more": True},
            }
            if page == 1
            else {
                "items": [
                    {"question": "q3", "answer": "a3", "kind": "gamma"},
                ],
                "meta": {"has_more": False},
            }
        )

    with patch("src.services.remote_data_sources._request_json", new=fake_request_json):
        first = await client.post(
            f"/api/data-sources/{source_id}/explore",
            json={"preset_id": preset_id},
        )
        assert first.status_code == 200
        first_data = first.json()
        assert first_data["mapped_rows"][0] == {
            "input": "q1",
            "expected_output": "a1",
            "category": "alpha",
        }
        assert first_data["next_page_state"] == {"page": 2}
        assert calls[0]["params"] == {"scope": "all", "page": 1, "limit": 2}

        second = await client.post(
            f"/api/data-sources/{source_id}/explore",
            json={
                "preset_id": preset_id,
                "page_state": first_data["next_page_state"],
            },
        )
        assert second.status_code == 200
        second_data = second.json()
        assert second_data["previous_page_state"] == {"page": 1}
        assert second_data["next_page_state"] is None
        assert second_data["mapped_rows"][0]["input"] == "q3"


@pytest.mark.asyncio
async def test_import_from_source_and_append_uses_dataset_snapshot_mapping(
    client: AsyncClient,
) -> None:
    """Appending after preset edits should keep using the dataset's frozen mapping snapshot."""
    source_id = await _create_source(client)
    preset_id = await _create_preset(client, source_id)

    create_dataset = await client.post(
        "/api/datasets/import-from-source",
        json={
            "name": "Imported Tickets",
            "preset_id": preset_id,
            "selected_records": [
                {"question": "q1", "answer": "a1", "kind": "alpha"},
                {"question": "q2", "answer": "a2", "kind": "beta"},
            ],
        },
    )
    assert create_dataset.status_code == 201
    dataset_id = create_dataset.json()["id"]
    assert create_dataset.json()["has_import_source"] is True

    first_detail = await client.get(f"/api/datasets/{dataset_id}")
    assert first_detail.status_code == 200
    assert first_detail.json()["rows"][0]["expected_output"] == "a1"

    update_preset = await client.put(
        f"/api/data-sources/{source_id}/presets/{preset_id}",
        json={
            "field_mapping": {
                "input": "question",
                "expected_output": "alt_answer",
                "category": "kind",
            }
        },
    )
    assert update_preset.status_code == 200

    append_rows = await client.post(
        f"/api/datasets/{dataset_id}/append-from-source",
        json={
            "selected_records": [
                {
                    "question": "q3",
                    "answer": "a3",
                    "alt_answer": "WRONG",
                    "kind": "gamma",
                }
            ]
        },
    )
    assert append_rows.status_code == 200
    appended = append_rows.json()
    assert appended["row_count"] == 3
    assert appended["rows"][-1]["expected_output"] == "a3"
    assert appended["import_source_snapshot"]["field_mapping"]["expected_output"] == "answer"

    delete_preset = await client.delete(f"/api/data-sources/{source_id}/presets/{preset_id}")
    assert delete_preset.status_code == 409


@pytest.mark.asyncio
async def test_import_from_source_without_preset_supports_template_mapping(
    client: AsyncClient,
) -> None:
    """A dataset may be created directly from an explored mapping without saving a preset."""
    source_id = await _create_source(client)

    create_dataset = await client.post(
        "/api/datasets/import-from-source",
        json={
            "name": "Imported Recipes",
            "data_source_id": source_id,
            "records_path": "$.recipes",
            "field_mapping": {
                "input": "Recipe: {name}\nIngredients: {ingredients}",
                "expected_output": "{instructions[0]} Then {instructions[1]}",
            },
            "selected_records": [
                {
                    "name": "Choco Chip Cookies",
                    "ingredients": ["Flour", "Butter"],
                    "instructions": ["Mix", "Bake"],
                }
            ],
        },
    )
    assert create_dataset.status_code == 201
    body = create_dataset.json()
    assert body["import_preset_id"] is None
    assert body["has_import_source"] is True

    dataset_id = body["id"]
    detail = await client.get(f"/api/datasets/{dataset_id}")
    assert detail.status_code == 200
    assert detail.json()["rows"][0]["input"] == 'Recipe: Choco Chip Cookies\nIngredients: ["Flour","Butter"]'
    assert detail.json()["rows"][0]["expected_output"] == "Mix Then Bake"
    assert detail.json()["import_source_snapshot"]["records_path"] == "$.recipes"


@pytest.mark.asyncio
async def test_import_from_source_supports_nested_conditional_mapping(
    client: AsyncClient,
) -> None:
    """Direct imports should honor conditional mapping expressions with nested arrays."""
    source_id = await _create_source(client)

    create_dataset = await client.post(
        "/api/datasets/import-from-source",
        json={
            "name": "Lot Labels",
            "data_source_id": source_id,
            "records_path": "$.logs",
            "field_mapping": {
                "input": "name",
                "expected_output": '{logs[].metadata[].lot_id = 12 ? "Lot 12" : "Other lot"}',
            },
            "selected_records": [
                {
                    "name": "alpha",
                    "logs": [
                        {
                            "metadata": [
                                {"lot_id": 12},
                                {"lot_id": 8},
                            ]
                        }
                    ],
                },
                {
                    "name": "beta",
                    "logs": [
                        {
                            "metadata": [
                                {"lot_id": 5},
                            ]
                        }
                    ],
                },
            ],
        },
    )
    assert create_dataset.status_code == 201

    dataset_id = create_dataset.json()["id"]
    detail = await client.get(f"/api/datasets/{dataset_id}")
    assert detail.status_code == 200
    assert detail.json()["rows"][0]["expected_output"] == "Lot 12"
    assert detail.json()["rows"][1]["expected_output"] == "Other lot"
