"""Helpers for duplicating data sources and their saved mappings."""

from __future__ import annotations

from src.db.models import DataSource
from src.db.repositories import DataSourceRepository, ImportPresetRepository


async def duplicate_data_source(
    source_id: str,
    *,
    source_repo: DataSourceRepository,
    preset_repo: ImportPresetRepository,
) -> DataSource | None:
    """Duplicate a data source and all of its import presets."""
    original = await source_repo.get_by_id(source_id)
    if original is None:
        return None

    duplicate = await source_repo.create(
        name=f"{original.name} copy",
        url=original.url,
        method=original.method,
        auth_type=original.auth_type,
        query_params=original.query_params or {},
        request_body=original.request_body,
        headers=original.headers or {},
        encrypted_secrets=original.encrypted_secrets,
        pagination_mode=original.pagination_mode,
        pagination_config=original.pagination_config or {},
    )

    presets = await preset_repo.list_by_data_source(source_id)
    for preset in reversed(presets):
        await preset_repo.create(
            data_source_id=duplicate.id,
            name=preset.name,
            records_path=preset.records_path,
            field_mapping=preset.field_mapping,
        )

    return duplicate
