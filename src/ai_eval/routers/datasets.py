"""Dataset upload and management routes — JSON API."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.config import get_settings
from ai_eval.db.repositories import DatasetRepository
from ai_eval.db.session import get_session
from ai_eval.routers.schemas.datasets import DatasetDetailResponse, DatasetResponse
from ai_eval.services.csv_parser import parse_csv

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

    metadata = await parse_csv(dataset.file_path)
    return DatasetDetailResponse(
        id=dataset.id,
        name=dataset.name,
        file_path=dataset.file_path,
        row_count=dataset.row_count,
        columns=dataset.columns,
        created_at=str(dataset.created_at),
        preview=metadata["preview"],
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
