"""Dataset upload and management routes — JSON API."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db.repositories import DatasetRepository, ImportPresetRepository
from src.db.session import get_session
from src.routers.schemas.data_sources import (
    AppendDatasetFromSourceRequest,
    ImportDatasetFromSourceRequest,
)
from src.routers.schemas.datasets import (
    DatasetDetailResponse,
    DatasetResponse,
    UpdateRowsRequest,
)
from src.services.dataset_imports import (
    append_imported_dataset_rows,
    create_imported_dataset,
)
from src.services.csv_parser import parse_csv, read_csv_rows, write_csv_rows
from src.services.csv_export import sanitize_export_name

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _dataset_to_response(dataset: object) -> DatasetResponse:
    """Convert a Dataset ORM object to a DatasetResponse."""
    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        file_path=dataset.file_path,
        row_count=dataset.row_count,
        columns=dataset.columns,
        import_preset_id=dataset.import_preset_id,
        has_import_source=dataset.import_source_snapshot is not None,
        created_at=str(dataset.created_at),
    )


@router.get("", response_model=list[DatasetResponse])
async def list_datasets(
    session: AsyncSession = Depends(get_session),
) -> list[DatasetResponse]:
    """List all uploaded datasets."""
    datasets = await DatasetRepository(session).list_all()
    return [_dataset_to_response(d) for d in datasets]


@router.post("", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    session: AsyncSession = Depends(get_session),
    name: str = Form(...),
    file: UploadFile = File(...),
) -> DatasetResponse:
    """Upload a CSV dataset."""
    settings = get_settings()
    file_name = f"{uuid4().hex}.csv"
    file_path = Path(settings.upload_dir) / file_name
    file_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    file_path.write_bytes(content)

    try:
        metadata = await parse_csv(str(file_path))
    except Exception:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Invalid CSV file")

    required = {"input", "expected_output"}
    if not required.issubset(set(metadata["columns"])):
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail="CSV must have 'input' and 'expected_output' columns",
        )

    dataset = await DatasetRepository(session).create(
        name=name,
        file_path=str(file_path),
        row_count=metadata["row_count"],
        columns=metadata["columns"],
    )
    return _dataset_to_response(dataset)


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
async def get_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_session),
) -> DatasetDetailResponse:
    """Return dataset detail with preview rows."""
    dataset = await DatasetRepository(session).get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    all_rows = await read_csv_rows(dataset.file_path)
    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        file_path=dataset.file_path,
        row_count=dataset.row_count,
        columns=dataset.columns,
        import_preset_id=dataset.import_preset_id,
        has_import_source=dataset.import_source_snapshot is not None,
        import_source_snapshot=dataset.import_source_snapshot,
        created_at=str(dataset.created_at),
        rows=all_rows,
    )


@router.get("/{dataset_id}/export")
async def export_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Download the full dataset as a CSV attachment."""
    dataset = await DatasetRepository(session).get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    filename = f"{sanitize_export_name(dataset.name, fallback='dataset')}.csv"
    return FileResponse(
        path=dataset.file_path,
        media_type="text/csv; charset=utf-8",
        filename=filename,
    )


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a dataset and its file."""
    repo = DatasetRepository(session)
    dataset = await repo.get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    Path(dataset.file_path).unlink(missing_ok=True)
    await repo.delete(dataset_id)


@router.post("/import-from-source", response_model=DatasetResponse, status_code=201)
async def import_dataset_from_source(
    body: ImportDatasetFromSourceRequest,
    session: AsyncSession = Depends(get_session),
) -> DatasetResponse:
    """Create a new dataset snapshot from selected remote rows."""
    import_preset_id: str | None = None
    data_source_id = body.data_source_id
    records_path = body.records_path
    field_mapping = body.field_mapping

    if body.preset_id is not None:
        preset = await ImportPresetRepository(session).get_by_id(body.preset_id)
        if preset is None:
            raise HTTPException(status_code=404, detail="Import preset not found")
        import_preset_id = preset.id
        data_source_id = preset.data_source_id
        records_path = preset.records_path
        field_mapping = preset.field_mapping

    try:
        dataset = await create_imported_dataset(
            session,
            name=body.name,
            data_source_id=str(data_source_id),
            records_path=str(records_path),
            field_mapping={str(key): str(value) for key, value in (field_mapping or {}).items()},
            selected_records=body.selected_records,
            import_preset_id=import_preset_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _dataset_to_response(dataset)


@router.put("/{dataset_id}/rows", response_model=DatasetDetailResponse)
async def update_dataset_rows(
    dataset_id: str,
    body: UpdateRowsRequest,
    session: AsyncSession = Depends(get_session),
) -> DatasetDetailResponse:
    """Overwrite all rows in the dataset CSV and update row_count."""
    repo = DatasetRepository(session)
    dataset = await repo.get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    columns = dataset.columns
    required = {"input", "expected_output"}
    if not required.issubset(set(columns)):
        raise HTTPException(status_code=422, detail="Dataset missing required columns")

    await write_csv_rows(dataset.file_path, columns, body.rows)

    new_count = len(body.rows)
    if new_count != dataset.row_count:
        await repo.update(dataset_id, row_count=new_count)
        dataset = await repo.get_by_id(dataset_id)

    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        file_path=dataset.file_path,
        row_count=dataset.row_count,
        columns=dataset.columns,
        import_preset_id=dataset.import_preset_id,
        has_import_source=dataset.import_source_snapshot is not None,
        import_source_snapshot=dataset.import_source_snapshot,
        created_at=str(dataset.created_at),
        rows=body.rows,
    )


@router.post("/{dataset_id}/append-from-source", response_model=DatasetDetailResponse)
async def append_dataset_from_source(
    dataset_id: str,
    body: AppendDatasetFromSourceRequest,
    session: AsyncSession = Depends(get_session),
) -> DatasetDetailResponse:
    """Append selected remote rows into an existing imported dataset."""
    repo = DatasetRepository(session)
    dataset = await repo.get_by_id(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        dataset = await append_imported_dataset_rows(
            session,
            dataset=dataset,
            selected_records=body.selected_records,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    rows = await read_csv_rows(dataset.file_path)
    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        file_path=dataset.file_path,
        row_count=dataset.row_count,
        columns=dataset.columns,
        import_preset_id=dataset.import_preset_id,
        has_import_source=dataset.import_source_snapshot is not None,
        import_source_snapshot=dataset.import_source_snapshot,
        created_at=str(dataset.created_at),
        rows=rows,
    )
