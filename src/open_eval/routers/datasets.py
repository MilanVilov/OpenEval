"""Dataset upload and management routes — JSON API."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from open_eval.config import get_settings
from open_eval.db.repositories import DatasetRepository
from open_eval.db.session import get_session
from open_eval.routers.schemas.datasets import (
    DatasetDetailResponse,
    DatasetResponse,
    UpdateRowsRequest,
)
from open_eval.services.csv_parser import parse_csv, read_csv_rows, write_csv_rows

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _dataset_to_response(dataset: object) -> DatasetResponse:
    """Convert a Dataset ORM object to a DatasetResponse."""
    return DatasetResponse(
        id=dataset.id,
        name=dataset.name,
        file_path=dataset.file_path,
        row_count=dataset.row_count,
        columns=dataset.columns,
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
        created_at=str(dataset.created_at),
        rows=all_rows,
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
        created_at=str(dataset.created_at),
        rows=body.rows,
    )
