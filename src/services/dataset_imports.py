"""Helpers for importing and appending datasets from remote source records."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db.models import Dataset
from src.db.repositories import DatasetRepository
from src.services.csv_parser import append_csv_rows, write_csv_rows
from src.services.remote_mapping import map_records


def build_import_source_snapshot(
    *,
    data_source_id: str,
    records_path: str,
    field_mapping: dict[str, str],
) -> dict[str, object]:
    """Build the frozen source snapshot stored on imported datasets."""
    return {
        "data_source_id": data_source_id,
        "records_path": records_path,
        "field_mapping": field_mapping,
    }


async def create_imported_dataset(
    session: AsyncSession,
    *,
    name: str,
    data_source_id: str,
    records_path: str,
    field_mapping: dict[str, str],
    selected_records: list[object],
    import_preset_id: str | None = None,
) -> Dataset:
    """Create a new dataset snapshot from selected remote records."""
    rows = _map_selected_records(
        selected_records,
        field_mapping=field_mapping,
    )
    columns = list(field_mapping.keys())
    file_path = _build_dataset_file_path()
    await write_csv_rows(str(file_path), columns, rows)

    snapshot = build_import_source_snapshot(
        data_source_id=data_source_id,
        records_path=records_path,
        field_mapping=field_mapping,
    )
    return await DatasetRepository(session).create(
        name=name,
        file_path=str(file_path),
        row_count=len(rows),
        columns=columns,
        import_preset_id=import_preset_id,
        import_source_snapshot=snapshot,
    )


async def append_imported_dataset_rows(
    session: AsyncSession,
    *,
    dataset: Dataset,
    selected_records: list[object],
) -> Dataset:
    """Append selected remote records into an existing imported dataset."""
    snapshot = dataset.import_source_snapshot
    if not isinstance(snapshot, dict):
        raise ValueError("Dataset does not support continuing import")

    field_mapping = snapshot.get("field_mapping")
    if not isinstance(field_mapping, dict):
        raise ValueError("Dataset import mapping is invalid")

    rows = _map_selected_records(
        selected_records,
        field_mapping={str(key): str(value) for key, value in field_mapping.items()},
        columns=list(dataset.columns),
    )
    await append_csv_rows(dataset.file_path, dataset.columns, rows)

    new_count = dataset.row_count + len(rows)
    updated = await DatasetRepository(session).update(dataset.id, row_count=new_count)
    assert updated is not None
    return updated


def _map_selected_records(
    selected_records: list[object],
    *,
    field_mapping: dict[str, str],
    columns: list[str] | None = None,
) -> list[dict[str, str]]:
    """Map selected source records into rows, validating the required fields."""
    if not selected_records:
        raise ValueError("Select at least one row to import")
    if "input" not in field_mapping or "expected_output" not in field_mapping:
        raise ValueError("Field mapping must include input and expected_output")
    return map_records(selected_records, field_mapping, columns=columns)


def _build_dataset_file_path() -> Path:
    """Return a new CSV file path for an imported dataset."""
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir / f"{uuid4().hex}.csv"
