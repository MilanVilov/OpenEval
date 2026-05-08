"""Remote data source and import preset routes — JSON API."""

from __future__ import annotations

import httpx

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories import DataSourceRepository, ImportPresetRepository
from src.db.session import get_session
from src.routers.schemas.data_sources import (
    DataSourceCreateRequest,
    DataSourceDetailResponse,
    DataSourceResponse,
    DataSourceUpdateRequest,
    ExploreDataSourceRequest,
    ExploreDataSourceResponse,
    ImportPresetCreateRequest,
    ImportPresetResponse,
    ImportPresetUpdateRequest,
)
from src.services.data_source_crypto import (
    decrypt_secret_payload,
    encrypt_secret_payload,
)
from src.services.remote_data_sources import explore_data_source

router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])


def _safe_secret_metadata(encrypted_secrets: str | None) -> tuple[bool, list[str]]:
    """Return whether secrets exist and which secret header names are present."""
    if not encrypted_secrets:
        return False, []
    try:
        secrets = decrypt_secret_payload(encrypted_secrets)
    except ValueError:
        return True, []

    secret_headers = secrets.get("secret_headers", {})
    header_names = sorted(secret_headers.keys()) if isinstance(secret_headers, dict) else []
    return True, header_names


def _source_to_response(source: object) -> DataSourceResponse:
    """Convert a data source ORM object to a response payload."""
    has_secret_credentials, secret_header_names = _safe_secret_metadata(
        source.encrypted_secrets,
    )
    return DataSourceResponse(
        id=source.id,
        name=source.name,
        url=source.url,
        method=source.method,
        auth_type=source.auth_type,
        pagination_mode=source.pagination_mode,
        has_secret_credentials=has_secret_credentials,
        secret_header_names=secret_header_names,
        created_at=str(source.created_at),
        updated_at=str(source.updated_at),
    )


def _source_to_detail_response(source: object) -> DataSourceDetailResponse:
    """Convert a data source ORM object to a detailed response payload."""
    base = _source_to_response(source)
    return DataSourceDetailResponse(
        **base.model_dump(),
        query_params=source.query_params or {},
        request_body=source.request_body,
        headers=source.headers or {},
        pagination_config=source.pagination_config or {},
    )


def _preset_to_response(preset: object) -> ImportPresetResponse:
    """Convert an import preset ORM object to a response payload."""
    return ImportPresetResponse(
        id=preset.id,
        data_source_id=preset.data_source_id,
        name=preset.name,
        records_path=preset.records_path,
        field_mapping=preset.field_mapping,
        created_at=str(preset.created_at),
        updated_at=str(preset.updated_at),
    )


def _build_secret_payload(
    *,
    auth_type: str,
    bearer_token: str | None,
    basic_username: str | None,
    basic_password: str | None,
    secret_headers: dict[str, str] | None,
) -> dict[str, object]:
    """Build the encrypted secret payload for a data source."""
    payload: dict[str, object] = {}
    if auth_type == "bearer":
        payload["bearer_token"] = bearer_token or ""
    if auth_type == "basic":
        payload["basic_username"] = basic_username or ""
        payload["basic_password"] = basic_password or ""
    if secret_headers:
        payload["secret_headers"] = secret_headers
    return payload


def _merge_source_update(
    existing_source: object,
    body: DataSourceUpdateRequest,
) -> tuple[dict[str, object], str | None]:
    """Merge an update request into the current source state."""
    fields = body.model_dump(exclude_unset=True)
    existing_secrets = decrypt_secret_payload(existing_source.encrypted_secrets)

    auth_type = str(fields.get("auth_type", existing_source.auth_type))
    secret_headers = (
        fields["secret_headers"]
        if "secret_headers" in fields
        else existing_secrets.get("secret_headers", {})
    )
    secret_payload = _build_secret_payload(
        auth_type=auth_type,
        bearer_token=(
            fields["bearer_token"]
            if "bearer_token" in fields
            else existing_secrets.get("bearer_token")
        ),
        basic_username=(
            fields["basic_username"]
            if "basic_username" in fields
            else existing_secrets.get("basic_username")
        ),
        basic_password=(
            fields["basic_password"]
            if "basic_password" in fields
            else existing_secrets.get("basic_password")
        ),
        secret_headers=secret_headers if isinstance(secret_headers, dict) else {},
    )

    merged = {
        "name": fields.get("name", existing_source.name),
        "url": fields.get("url", existing_source.url),
        "method": fields.get("method", existing_source.method),
        "auth_type": auth_type,
        "query_params": fields.get("query_params", existing_source.query_params or {}),
        "request_body": fields.get("request_body", existing_source.request_body),
        "headers": fields.get("headers", existing_source.headers or {}),
        "pagination_mode": fields.get(
            "pagination_mode",
            existing_source.pagination_mode,
        ),
        "pagination_config": fields.get(
            "pagination_config",
            existing_source.pagination_config or {},
        ),
        "bearer_token": secret_payload.get("bearer_token"),
        "basic_username": secret_payload.get("basic_username"),
        "basic_password": secret_payload.get("basic_password"),
        "secret_headers": secret_payload.get("secret_headers", {}),
    }
    validated = DataSourceCreateRequest(**merged)
    encrypted = encrypt_secret_payload(secret_payload)

    return {
        "name": validated.name,
        "url": validated.url,
        "method": validated.method,
        "auth_type": validated.auth_type,
        "query_params": validated.query_params,
        "request_body": validated.request_body,
        "headers": validated.headers,
        "pagination_mode": validated.pagination_mode,
        "pagination_config": validated.pagination_config,
    }, encrypted


@router.get("", response_model=list[DataSourceResponse])
async def list_data_sources(
    session: AsyncSession = Depends(get_session),
) -> list[DataSourceResponse]:
    """List all data sources."""
    sources = await DataSourceRepository(session).list_all()
    return [_source_to_response(source) for source in sources]


@router.post("", response_model=DataSourceResponse, status_code=201)
async def create_data_source(
    body: DataSourceCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> DataSourceResponse:
    """Create a new data source."""
    encrypted = encrypt_secret_payload(
        _build_secret_payload(
            auth_type=body.auth_type,
            bearer_token=body.bearer_token,
            basic_username=body.basic_username,
            basic_password=body.basic_password,
            secret_headers=body.secret_headers,
        ),
    )
    source = await DataSourceRepository(session).create(
        name=body.name,
        url=body.url,
        method=body.method,
        auth_type=body.auth_type,
        query_params=body.query_params,
        request_body=body.request_body,
        headers=body.headers,
        encrypted_secrets=encrypted,
        pagination_mode=body.pagination_mode,
        pagination_config=body.pagination_config,
    )
    return _source_to_response(source)


@router.get("/{source_id}", response_model=DataSourceDetailResponse)
async def get_data_source(
    source_id: str,
    session: AsyncSession = Depends(get_session),
) -> DataSourceDetailResponse:
    """Return a single data source."""
    source = await DataSourceRepository(session).get_by_id(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    return _source_to_detail_response(source)


@router.put("/{source_id}", response_model=DataSourceDetailResponse)
async def update_data_source(
    source_id: str,
    body: DataSourceUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> DataSourceDetailResponse:
    """Update a data source."""
    repo = DataSourceRepository(session)
    source = await repo.get_by_id(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    if not body.model_dump(exclude_unset=True):
        raise HTTPException(status_code=422, detail="No fields to update")

    fields, encrypted = _merge_source_update(source, body)
    updated = await repo.update(source_id, **fields, encrypted_secrets=encrypted)
    assert updated is not None
    return _source_to_detail_response(updated)


@router.delete("/{source_id}", status_code=204)
async def delete_data_source(
    source_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a data source."""
    repo = DataSourceRepository(session)
    source = await repo.get_by_id(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    try:
        await repo.delete(source_id)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Delete import presets or imported datasets before removing this data source",
        ) from exc


@router.get("/{source_id}/presets", response_model=list[ImportPresetResponse])
async def list_import_presets(
    source_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[ImportPresetResponse]:
    """List all presets for a data source."""
    if await DataSourceRepository(session).get_by_id(source_id) is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    presets = await ImportPresetRepository(session).list_by_data_source(source_id)
    return [_preset_to_response(preset) for preset in presets]


@router.post("/{source_id}/presets", response_model=ImportPresetResponse, status_code=201)
async def create_import_preset(
    source_id: str,
    body: ImportPresetCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> ImportPresetResponse:
    """Create a new import preset for a data source."""
    if await DataSourceRepository(session).get_by_id(source_id) is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    preset = await ImportPresetRepository(session).create(
        data_source_id=source_id,
        name=body.name,
        records_path=body.records_path,
        field_mapping=body.field_mapping,
    )
    return _preset_to_response(preset)


@router.get("/{source_id}/presets/{preset_id}", response_model=ImportPresetResponse)
async def get_import_preset(
    source_id: str,
    preset_id: str,
    session: AsyncSession = Depends(get_session),
) -> ImportPresetResponse:
    """Return a single import preset."""
    preset = await ImportPresetRepository(session).get_by_id(preset_id)
    if preset is None or preset.data_source_id != source_id:
        raise HTTPException(status_code=404, detail="Import preset not found")
    return _preset_to_response(preset)


@router.put("/{source_id}/presets/{preset_id}", response_model=ImportPresetResponse)
async def update_import_preset(
    source_id: str,
    preset_id: str,
    body: ImportPresetUpdateRequest,
    session: AsyncSession = Depends(get_session),
) -> ImportPresetResponse:
    """Update an import preset."""
    repo = ImportPresetRepository(session)
    preset = await repo.get_by_id(preset_id)
    if preset is None or preset.data_source_id != source_id:
        raise HTTPException(status_code=404, detail="Import preset not found")

    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=422, detail="No fields to update")
    updated = await repo.update(preset_id, **fields)
    assert updated is not None
    return _preset_to_response(updated)


@router.delete("/{source_id}/presets/{preset_id}", status_code=204)
async def delete_import_preset(
    source_id: str,
    preset_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an import preset."""
    repo = ImportPresetRepository(session)
    preset = await repo.get_by_id(preset_id)
    if preset is None or preset.data_source_id != source_id:
        raise HTTPException(status_code=404, detail="Import preset not found")
    try:
        await repo.delete(preset_id)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Delete imported datasets before removing this preset",
        ) from exc


@router.post("/{source_id}/explore", response_model=ExploreDataSourceResponse)
async def explore_remote_data_source(
    source_id: str,
    body: ExploreDataSourceRequest,
    session: AsyncSession = Depends(get_session),
) -> ExploreDataSourceResponse:
    """Fetch and inspect a page from a remote data source."""
    source = await DataSourceRepository(session).get_by_id(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    records_path = body.records_path
    field_mapping = body.field_mapping
    if body.preset_id:
        preset = await ImportPresetRepository(session).get_by_id(body.preset_id)
        if preset is None or preset.data_source_id != source_id:
            raise HTTPException(status_code=404, detail="Import preset not found")
        if records_path is None:
            records_path = preset.records_path
        if field_mapping is None:
            field_mapping = preset.field_mapping

    try:
        result = await explore_data_source(
            source,
            page_state=body.page_state,
            records_path=records_path,
            field_mapping=field_mapping,
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Remote request failed with status {exc.response.status_code}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=422, detail=f"Remote request failed: {exc}") from exc
    except ValueError as exc:
        status = 500 if "DATA_SOURCE_ENCRYPTION_KEY" in str(exc) else 422
        raise HTTPException(status_code=status, detail=str(exc)) from exc

    return ExploreDataSourceResponse(
        request_summary=result.request_summary,
        raw_response=result.raw_response,
        candidate_array_paths=result.candidate_array_paths,
        field_candidates=result.field_candidates,
        records=result.records,
        mapped_rows=result.mapped_rows,
        current_page_state=result.current_page_state,
        next_page_state=result.next_page_state,
        previous_page_state=result.previous_page_state,
    )
