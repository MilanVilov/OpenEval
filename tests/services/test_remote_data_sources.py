"""Tests for remote data source exploration helpers."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from src.db.models import DataSource
from src.services.remote_data_sources import explore_data_source


@pytest.mark.asyncio
async def test_explore_data_source_without_pagination_has_no_page_states() -> None:
    """None pagination should not emit previous or next page states."""
    source = DataSource(
        name="Users",
        url="https://example.test/users",
        method="GET",
        auth_type="none",
        query_params={},
        request_body=None,
        headers={},
        encrypted_secrets=None,
        pagination_mode="none",
        pagination_config={},
    )

    async def fake_request(self, method, url, params=None, json=None, headers=None):
        return httpx.Response(
            200,
            json={"items": [{"question": "q1", "answer": "a1"}]},
            request=httpx.Request(method, url),
        )

    with patch("httpx.AsyncClient.request", new=fake_request):
        result = await explore_data_source(
            source,
            records_path="$.items",
            field_mapping={"input": "question", "expected_output": "answer"},
        )

    assert result.current_page_state is None
    assert result.next_page_state is None
    assert result.previous_page_state is None


@pytest.mark.asyncio
async def test_explore_data_source_offset_pagination_sets_params() -> None:
    """Offset pagination should emit limit and offset values and next state."""
    source = DataSource(
        name="Users",
        url="https://example.test/users",
        method="GET",
        auth_type="none",
        query_params={"scope": "all"},
        request_body=None,
        headers={},
        encrypted_secrets=None,
        pagination_mode="offset",
        pagination_config={
            "offset_param": "skip",
            "limit_param": "take",
            "page_size": 10,
            "has_more_path": "$.meta.has_more",
        },
    )
    calls: list[dict[str, object]] = []

    async def fake_request(self, method, url, params=None, json=None, headers=None):
        calls.append({"params": params})
        return httpx.Response(
            200,
            json={
                "items": [{"question": "q1", "answer": "a1"}],
                "meta": {"has_more": True},
            },
            request=httpx.Request(method, url),
        )

    with patch("httpx.AsyncClient.request", new=fake_request):
        result = await explore_data_source(
            source,
            records_path="$.items",
            field_mapping={"input": "question", "expected_output": "answer"},
        )

    assert calls[0]["params"] == {"scope": "all", "skip": 0, "take": 10}
    assert result.next_page_state == {"offset": 10}
    assert result.previous_page_state is None


@pytest.mark.asyncio
async def test_explore_data_source_next_token_tracks_history() -> None:
    """Next-token pagination should emit a next token and a reversible history."""
    source = DataSource(
        name="Users",
        url="https://example.test/users",
        method="GET",
        auth_type="none",
        query_params={},
        request_body=None,
        headers={},
        encrypted_secrets=None,
        pagination_mode="next_token",
        pagination_config={
            "token_param": "cursor",
            "response_token_path": "$.paging.next",
        },
    )
    calls: list[dict[str, object]] = []

    async def fake_request(self, method, url, params=None, json=None, headers=None):
        calls.append({"params": params})
        cursor = None if params is None else params.get("cursor")
        payload = (
            {
                "items": [{"question": "q1", "answer": "a1"}],
                "paging": {"next": "cursor-2"},
            }
            if cursor is None
            else {
                "items": [{"question": "q2", "answer": "a2"}],
                "paging": {"next": None},
            }
        )
        return httpx.Response(200, json=payload, request=httpx.Request(method, url))

    with patch("httpx.AsyncClient.request", new=fake_request):
        first = await explore_data_source(
            source,
            records_path="$.items",
            field_mapping={"input": "question", "expected_output": "answer"},
        )
        second = await explore_data_source(
            source,
            page_state=first.next_page_state,
            records_path="$.items",
            field_mapping={"input": "question", "expected_output": "answer"},
        )

    assert calls[0]["params"] == {}
    assert first.next_page_state == {"token": "cursor-2", "history": [None]}
    assert second.previous_page_state == {"token": None, "history": []}
    assert calls[1]["params"] == {"cursor": "cursor-2"}


@pytest.mark.asyncio
async def test_explore_data_source_includes_auth_and_secret_headers() -> None:
    """Bearer auth and secret headers should be injected into remote requests."""
    from cryptography.fernet import Fernet

    from src.services.data_source_crypto import encrypt_secret_payload

    source = DataSource(
        name="Users",
        url="https://example.test/users",
        method="GET",
        auth_type="bearer",
        query_params={},
        request_body=None,
        headers={"X-Public": "visible"},
        encrypted_secrets=None,
        pagination_mode="none",
        pagination_config={},
    )
    calls: list[dict[str, object]] = []

    async def fake_request(self, method, url, params=None, json=None, headers=None):
        calls.append({"headers": headers})
        return httpx.Response(
            200,
            json={"items": [{"question": "q1", "answer": "a1"}]},
            request=httpx.Request(method, url),
        )

    with (
        patch(
            "src.services.data_source_crypto.get_settings",
            return_value=type(
                "Settings",
                (),
                {"data_source_encryption_key": Fernet.generate_key().decode("utf-8")},
            )(),
        ),
    ):
        source.encrypted_secrets = encrypt_secret_payload(
            {
                "bearer_token": "secret-token",
                "secret_headers": {"X-Api-Key": "abc"},
            }
        )
        with patch("httpx.AsyncClient.request", new=fake_request):
            await explore_data_source(
                source,
                records_path="$.items",
                field_mapping={"input": "question", "expected_output": "answer"},
            )

    assert calls[0]["headers"]["Authorization"] == "Bearer secret-token"
    assert calls[0]["headers"]["X-Api-Key"] == "abc"
    assert calls[0]["headers"]["X-Public"] == "visible"
