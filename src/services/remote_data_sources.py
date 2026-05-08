"""Remote data source request execution and exploration helpers."""

from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass

import httpx

from src.db.models import DataSource
from src.services.data_source_crypto import decrypt_secret_payload
from src.services.remote_mapping import (
    extract_records,
    find_array_paths,
    list_field_candidates,
    map_records,
    resolve_path,
)


@dataclass
class ExploreResult:
    """Result of exploring a remote data source."""

    request_summary: dict[str, object]
    raw_response: object
    candidate_array_paths: list[str]
    field_candidates: list[str]
    records: list[object]
    mapped_rows: list[dict[str, str]]
    current_page_state: dict[str, object] | None
    next_page_state: dict[str, object] | None
    previous_page_state: dict[str, object] | None


async def explore_data_source(
    data_source: DataSource,
    *,
    page_state: dict[str, object] | None = None,
    records_path: str | None = None,
    field_mapping: dict[str, str] | None = None,
) -> ExploreResult:
    """Fetch and inspect a single page from a remote data source."""
    request_params = dict(data_source.query_params or {})
    request_body = deepcopy(data_source.request_body)
    current_state = _normalize_page_state(
        data_source.pagination_mode,
        data_source.pagination_config or {},
        page_state,
    )
    _apply_page_state(
        request_params,
        request_body,
        data_source.pagination_mode,
        data_source.pagination_config or {},
        current_state,
    )

    payload = await _request_json(data_source, request_params=request_params, request_body=request_body)
    candidate_array_paths = find_array_paths(payload)
    records = extract_records(payload, records_path)
    mapped_rows = map_records(records, field_mapping or {}) if records and field_mapping else []
    field_candidates = list_field_candidates(records) if records else []

    previous_page_state = _build_previous_page_state(
        data_source.pagination_mode,
        data_source.pagination_config or {},
        current_state,
    )
    next_page_state = _build_next_page_state(
        payload,
        candidate_array_paths,
        records,
        data_source.pagination_mode,
        data_source.pagination_config or {},
        current_state,
    )

    return ExploreResult(
        request_summary=_build_request_summary(
            data_source,
            request_params=request_params,
            request_body=request_body,
        ),
        raw_response=payload,
        candidate_array_paths=candidate_array_paths,
        field_candidates=field_candidates,
        records=records,
        mapped_rows=mapped_rows,
        current_page_state=current_state,
        next_page_state=next_page_state,
        previous_page_state=previous_page_state,
    )


async def _request_json(
    data_source: DataSource,
    *,
    request_params: dict[str, object],
    request_body: dict | list | None,
) -> object:
    """Execute the remote request and return a parsed JSON payload."""
    headers = _build_request_headers(data_source)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            data_source.method,
            data_source.url,
            params=request_params,
            json=request_body if data_source.method.upper() == "POST" else None,
            headers=headers,
        )
    response.raise_for_status()

    try:
        return response.json()
    except ValueError as exc:
        raise ValueError("Remote endpoint must return JSON") from exc


def _build_request_headers(data_source: DataSource) -> dict[str, str]:
    """Build request headers including decrypted secret values."""
    secrets = decrypt_secret_payload(data_source.encrypted_secrets)
    headers = {str(key): str(value) for key, value in (data_source.headers or {}).items()}
    secret_headers = secrets.get("secret_headers", {})
    if isinstance(secret_headers, dict):
        for key, value in secret_headers.items():
            headers[str(key)] = str(value)

    if data_source.auth_type == "bearer" and isinstance(secrets.get("bearer_token"), str):
        headers["Authorization"] = f"Bearer {secrets['bearer_token']}"
    if data_source.auth_type == "basic":
        username = secrets.get("basic_username", "")
        password = secrets.get("basic_password", "")
        if isinstance(username, str) and isinstance(password, str):
            token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {token}"

    return headers


def _build_request_summary(
    data_source: DataSource,
    *,
    request_params: dict[str, object],
    request_body: dict | list | None,
) -> dict[str, object]:
    """Return a safe request summary for UI display."""
    secrets = decrypt_secret_payload(data_source.encrypted_secrets)
    secret_headers = secrets.get("secret_headers", {})
    header_names = sorted(secret_headers.keys()) if isinstance(secret_headers, dict) else []
    return {
        "method": data_source.method,
        "url": data_source.url,
        "query_params": request_params,
        "request_body": request_body,
        "headers": data_source.headers or {},
        "auth_type": data_source.auth_type,
        "has_secret_credentials": bool(secrets),
        "secret_header_names": header_names,
        "pagination_mode": data_source.pagination_mode,
    }


def _normalize_page_state(
    mode: str,
    config: dict,
    page_state: dict[str, object] | None,
) -> dict[str, object] | None:
    """Normalize pagination state for the given mode."""
    if mode == "none":
        return None
    if mode == "page":
        start_page = _int_value(config.get("start_page"), default=1)
        current_page = _int_value((page_state or {}).get("page"), default=start_page)
        return {"page": current_page}
    if mode == "offset":
        start_offset = _int_value(config.get("start_offset"), default=0)
        current_offset = _int_value((page_state or {}).get("offset"), default=start_offset)
        return {"offset": current_offset}
    if mode == "next_token":
        state = dict(page_state or {})
        history = state.get("history")
        return {
            "token": state.get("token", config.get("initial_token")),
            "history": list(history) if isinstance(history, list) else [],
        }
    raise ValueError(f"Unsupported pagination mode: {mode}")


def _apply_page_state(
    request_params: dict[str, object],
    request_body: dict | list | None,
    mode: str,
    config: dict,
    page_state: dict[str, object] | None,
) -> None:
    """Apply the current pagination state to request params or body."""
    if mode == "none" or page_state is None:
        return

    placement = str(config.get("placement", "query"))
    if mode == "page":
        page_param = str(config.get("page_param", "page"))
        _set_request_value(
            request_params,
            request_body,
            page_param,
            page_state["page"],
            placement=placement,
        )
        page_size = config.get("page_size")
        page_size_param = config.get("page_size_param")
        if page_size is not None and page_size_param:
            _set_request_value(
                request_params,
                request_body,
                str(page_size_param),
                page_size,
                placement=placement,
            )
        return

    if mode == "offset":
        offset_param = str(config.get("offset_param", "offset"))
        limit_param = str(config.get("limit_param", "limit"))
        page_size = _int_value(config.get("page_size"), default=50)
        _set_request_value(
            request_params,
            request_body,
            offset_param,
            page_state["offset"],
            placement=placement,
        )
        _set_request_value(
            request_params,
            request_body,
            limit_param,
            page_size,
            placement=placement,
        )
        return

    if mode == "next_token":
        token = page_state.get("token")
        if token in (None, ""):
            return
        token_param = str(config.get("token_param", "page_token"))
        _set_request_value(
            request_params,
            request_body,
            token_param,
            token,
            placement=placement,
        )


def _build_previous_page_state(
    mode: str,
    config: dict,
    page_state: dict[str, object] | None,
) -> dict[str, object] | None:
    """Return the previous page state for the current page, if available."""
    if page_state is None:
        return None
    if mode == "page":
        start_page = _int_value(config.get("start_page"), default=1)
        current_page = _int_value(page_state.get("page"), default=start_page)
        if current_page <= start_page:
            return None
        return {"page": current_page - 1}
    if mode == "offset":
        start_offset = _int_value(config.get("start_offset"), default=0)
        page_size = _int_value(config.get("page_size"), default=50)
        current_offset = _int_value(page_state.get("offset"), default=start_offset)
        if current_offset <= start_offset:
            return None
        return {"offset": max(start_offset, current_offset - page_size)}
    if mode == "next_token":
        history = page_state.get("history", [])
        if not isinstance(history, list) or not history:
            return None
        return {
            "token": history[-1],
            "history": history[:-1],
        }
    return None


def _build_next_page_state(
    payload: object,
    candidate_array_paths: list[str],
    records: list[object],
    mode: str,
    config: dict,
    page_state: dict[str, object] | None,
) -> dict[str, object] | None:
    """Return the next page state when more data appears to be available."""
    if page_state is None or mode == "none":
        return None
    if mode == "next_token":
        token_path = str(config.get("response_token_path", "next_token"))
        next_token = resolve_path(payload, token_path)
        if next_token in (None, ""):
            return None
        history = page_state.get("history", [])
        if not isinstance(history, list):
            history = []
        return {"token": next_token, "history": [*history, page_state.get("token")]}

    has_more = _extract_has_more(payload, config)
    if has_more is None:
        has_more = _response_has_items(payload, candidate_array_paths, records)
    if not has_more:
        return None

    if mode == "page":
        return {"page": _int_value(page_state.get("page"), default=1) + 1}
    if mode == "offset":
        page_size = _int_value(config.get("page_size"), default=50)
        return {"offset": _int_value(page_state.get("offset"), default=0) + page_size}
    return None


def _extract_has_more(payload: object, config: dict) -> bool | None:
    """Resolve an optional has-more flag from the response payload."""
    has_more_path = config.get("has_more_path")
    if not has_more_path:
        return None
    value = resolve_path(payload, str(has_more_path))
    return value if isinstance(value, bool) else None


def _response_has_items(
    payload: object,
    candidate_array_paths: list[str],
    records: list[object],
) -> bool:
    """Infer whether the response seems to have page data."""
    if records:
        return True
    if isinstance(payload, list):
        return bool(payload)
    for path in candidate_array_paths:
        value = resolve_path(payload, path)
        if isinstance(value, list) and value:
            return True
    if isinstance(payload, dict):
        return bool(payload)
    return False


def _set_request_value(
    request_params: dict[str, object],
    request_body: dict | list | None,
    key: str,
    value: object,
    *,
    placement: str,
) -> None:
    """Set a pagination value in query params or a JSON body dictionary."""
    if placement == "body" and isinstance(request_body, dict):
        request_body[key] = value
        return
    request_params[key] = value


def _int_value(value: object, *, default: int) -> int:
    """Convert ``value`` to an int, falling back to ``default``."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return default
    return default
