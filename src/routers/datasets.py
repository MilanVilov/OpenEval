"""Dataset upload and management routes — JSON API."""

import csv
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories import DatasetRepository, ImportPresetRepository
from src.db.session import get_session
from src.routers.schemas.data_sources import (
    AppendDatasetFromSourceRequest,
    ImportDatasetFromSourceRequest,
)
from src.routers.schemas.datasets import (
    DatasetDetailResponse,
    DatasetResponse,
    PaginatedDatasetResponse,
    UpdateRowsRequest,
)
from src.services.csv_export import sanitize_export_name
from src.services.csv_parser import parse_csv_content
from src.services.dataset_imports import (
    append_imported_dataset_rows,
    create_imported_dataset,
)
from src.services.dataset_storage import (
    build_dataset_file_path,
    decode_csv_upload,
    read_dataset_rows,
    serialize_dataset_rows,
    write_dataset_file_copy,
)

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


def _csv_response(csv_content: str, filename: str) -> Response:
    """Return CSV content as a downloadable attachment."""
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("", response_model=list[DatasetResponse] | PaginatedDatasetResponse)
async def list_datasets(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int | None, Query(ge=1)] = None,
    page_size: Annotated[int | None, Query(ge=1, le=100)] = None,
    search: str | None = None,
) -> list[DatasetResponse] | PaginatedDatasetResponse:
    """List all uploaded datasets."""
    repo = DatasetRepository(session)
    if page is None and page_size is None and search is None:
        datasets = await repo.list_all()
        return [_dataset_to_response(d) for d in datasets]

    requested_page = page or 1
    requested_page_size = page_size or 10
    result = await repo.list_page(
        page=requested_page,
        page_size=requested_page_size,
        search=search,
    )
    pages = (result.total + requested_page_size - 1) // requested_page_size or 1
    datasets = [_dataset_to_response(d) for d in result.items]
    return PaginatedDatasetResponse(
        items=datasets,
        total=result.total,
        page=requested_page,
        page_size=requested_page_size,
        pages=pages,
        search=search.strip() if search else None,
    )


@router.post("", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    session: AsyncSession = Depends(get_session),
    name: str = Form(...),
    file: UploadFile = File(...),
) -> DatasetResponse:
    """Upload a CSV dataset."""
    content = await file.read()
    file_path = build_dataset_file_path()

    try:
        csv_content = decode_csv_upload(content)
        metadata = parse_csv_content(csv_content)
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(status_code=422, detail="Invalid CSV file") from exc

    required = {"input", "expected_output"}
    if not required.issubset(set(metadata["columns"])):
        raise HTTPException(
            status_code=422,
            detail="CSV must have 'input' and 'expected_output' columns",
        )

    write_dataset_file_copy(str(file_path), csv_content)
    dataset = await DatasetRepository(session).create(
        name=name,
        file_path=str(file_path),
        csv_content=csv_content,
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
    dataset = await DatasetRepository(session).get_by_id_with_content(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    all_rows = await read_dataset_rows(dataset)
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
) -> Response:
    """Download the full dataset as a CSV attachment."""
    dataset = await DatasetRepository(session).get_by_id_with_content(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    filename = f"{sanitize_export_name(dataset.name, fallback='dataset')}.csv"
    if dataset.csv_content is not None:
        return _csv_response(dataset.csv_content, filename)

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
            selected_rows=body.selected_rows,
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

    csv_content = serialize_dataset_rows(columns, body.rows)
    write_dataset_file_copy(dataset.file_path, csv_content)

    new_count = len(body.rows)
    await repo.update(dataset_id, row_count=new_count, csv_content=csv_content)
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
    dataset = await repo.get_by_id_with_content(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        dataset = await append_imported_dataset_rows(
            session,
            dataset=dataset,
            selected_records=body.selected_records,
            selected_rows=body.selected_rows,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    rows = await read_dataset_rows(dataset)
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
