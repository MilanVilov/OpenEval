"""Vector store management routes."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.app import templates
from ai_eval.config import get_settings
from ai_eval.db.repositories import VectorStoreRepository
from ai_eval.db.session import get_session
from ai_eval.services.openai_client import (
    create_vector_store,
    delete_vector_store,
    get_vector_store_info,
    upload_file_to_vector_store,
)

router = APIRouter(prefix="/vector-stores", tags=["vector-stores"])


@router.get("", response_class=HTMLResponse)
async def list_vector_stores(request: Request, session: AsyncSession = Depends(get_session)):
    """List all vector stores."""
    stores = await VectorStoreRepository(session).list_all()
    return templates.TemplateResponse(
        "vector_stores/list.html",
        {"request": request, "active_page": "vector_stores", "stores": stores},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_vector_store(request: Request):
    """Render the create vector store form."""
    return templates.TemplateResponse(
        "vector_stores/new.html",
        {"request": request, "active_page": "vector_stores"},
    )


@router.post("", response_class=HTMLResponse)
async def create_vector_store_route(
    request: Request,
    session: AsyncSession = Depends(get_session),
    name: str = Form(...),
):
    """Create a new vector store in OpenAI and save to DB."""
    try:
        result = await create_vector_store(name)
    except Exception as exc:
        return templates.TemplateResponse(
            "vector_stores/new.html",
            {
                "request": request,
                "active_page": "vector_stores",
                "error": f"OpenAI API error: {exc}",
                "name": name,
            },
            status_code=422,
        )

    store = await VectorStoreRepository(session).create(
        openai_vector_store_id=result["id"],
        name=name,
        status=result["status"],
    )
    return RedirectResponse(f"/vector-stores/{store.id}", status_code=303)


@router.get("/{store_id}", response_class=HTMLResponse)
async def detail_vector_store(
    store_id: str, request: Request, session: AsyncSession = Depends(get_session),
):
    """Show vector store detail, refreshing status from OpenAI."""
    repo = VectorStoreRepository(session)
    store = await repo.get_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Vector store not found")

    # Fetch fresh info from OpenAI and update DB if changed
    try:
        info = await get_vector_store_info(store.openai_vector_store_id)
        updates: dict = {}
        if info["status"] != store.status:
            updates["status"] = info["status"]
        if info["file_counts"] != store.file_count:
            updates["file_count"] = info["file_counts"]
        if updates:
            store = await repo.update(store_id, **updates)
    except Exception:
        pass  # Show stale data if OpenAI is unreachable

    return templates.TemplateResponse(
        "vector_stores/detail.html",
        {"request": request, "active_page": "vector_stores", "store": store},
    )


@router.post("/{store_id}/files", response_class=HTMLResponse)
async def upload_file(
    store_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    file: UploadFile = File(...),
):
    """Upload a file to a vector store."""
    repo = VectorStoreRepository(session)
    store = await repo.get_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Vector store not found")

    settings = get_settings()
    temp_name = f"{uuid4().hex}_{file.filename}"
    temp_path = Path(settings.upload_dir) / temp_name

    content = await file.read()
    temp_path.write_bytes(content)

    try:
        await upload_file_to_vector_store(
            store.openai_vector_store_id, str(temp_path), file.filename or temp_name,
        )
        await repo.update(store_id, file_count=store.file_count + 1)
    except Exception as exc:
        return templates.TemplateResponse(
            "vector_stores/detail.html",
            {
                "request": request,
                "active_page": "vector_stores",
                "store": store,
                "error": f"Upload failed: {exc}",
            },
            status_code=422,
        )
    finally:
        temp_path.unlink(missing_ok=True)

    return RedirectResponse(f"/vector-stores/{store_id}", status_code=303)


@router.delete("/{store_id}")
async def delete_vector_store_route(
    store_id: str, session: AsyncSession = Depends(get_session),
):
    """Delete a vector store from OpenAI and DB."""
    repo = VectorStoreRepository(session)
    store = await repo.get_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Vector store not found")

    await delete_vector_store(store.openai_vector_store_id)
    await repo.delete(store_id)
    return Response(status_code=200, headers={"HX-Redirect": "/vector-stores"})
