"""Dataset upload and management routes."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.app import templates
from ai_eval.config import get_settings
from ai_eval.db.repositories import DatasetRepository
from ai_eval.db.session import get_session
from ai_eval.services.csv_parser import parse_csv

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_class=HTMLResponse)
async def list_datasets(request: Request, session: AsyncSession = Depends(get_session)):
    """List all uploaded datasets."""
    datasets = await DatasetRepository(session).list_all()
    return templates.TemplateResponse(
        "datasets/list.html",
        {"request": request, "active_page": "datasets", "datasets": datasets},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_dataset(request: Request):
    """Render the dataset upload form."""
    return templates.TemplateResponse(
        "datasets/new.html",
        {"request": request, "active_page": "datasets"},
    )


@router.post("", response_class=HTMLResponse)
async def upload_dataset(
    request: Request,
    session: AsyncSession = Depends(get_session),
    name: str = Form(...),
    file: UploadFile = File(...),
):
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
        return templates.TemplateResponse(
            "datasets/new.html",
            {"request": request, "active_page": "datasets", "error": "Invalid CSV file."},
            status_code=422,
        )

    required = {"input", "expected_output"}
    if not required.issubset(set(metadata["columns"])):
        file_path.unlink(missing_ok=True)
        return templates.TemplateResponse(
            "datasets/new.html",
            {
                "request": request,
                "active_page": "datasets",
                "error": "CSV must have 'input' and 'expected_output' columns.",
                "name": name,
            },
            status_code=422,
        )

    dataset = await DatasetRepository(session).create(
        name=name,
        file_path=str(file_path),
        row_count=metadata["row_count"],
        columns=metadata["columns"],
    )
    return RedirectResponse(f"/datasets/{dataset.id}", status_code=303)


@router.get("/{dataset_id}", response_class=HTMLResponse)
async def detail_dataset(
    dataset_id: str, request: Request, session: AsyncSession = Depends(get_session),
):
    """Show dataset detail with preview."""
    dataset = await DatasetRepository(session).get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    metadata = await parse_csv(dataset.file_path)
    return templates.TemplateResponse(
        "datasets/detail.html",
        {"request": request, "active_page": "datasets", "dataset": dataset, "preview": metadata["preview"]},
    )


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str, session: AsyncSession = Depends(get_session),
):
    """Delete a dataset and its file."""
    repo = DatasetRepository(session)
    dataset = await repo.get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    Path(dataset.file_path).unlink(missing_ok=True)
    await repo.delete(dataset_id)
    return Response(status_code=200, headers={"HX-Redirect": "/datasets"})
