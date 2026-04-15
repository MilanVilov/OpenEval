"""Vector store management routes — JSON API."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db.repositories import VectorStoreRepository
from src.db.session import get_session
from src.routers.schemas.vector_stores import (
    CreateVectorStoreRequest,
    VectorStoreResponse,
)
from src.services.openai_client import (
    create_vector_store,
    delete_vector_store,
    get_vector_store_info,
    upload_file_to_vector_store,
)

router = APIRouter(prefix="/api/vector-stores", tags=["vector-stores"])


def _store_to_response(store: object) -> VectorStoreResponse:
    """Convert a VectorStore ORM object to a VectorStoreResponse."""
    return VectorStoreResponse(
        id=store.id,
        openai_vector_store_id=store.openai_vector_store_id,
        name=store.name,
        file_count=store.file_count,
        status=store.status,
        created_at=str(store.created_at),
    )


@router.get("", response_model=list[VectorStoreResponse])
async def list_vector_stores(
    session: AsyncSession = Depends(get_session),
) -> list[VectorStoreResponse]:
    """List all vector stores."""
    stores = await VectorStoreRepository(session).list_all()
    return [_store_to_response(s) for s in stores]


@router.post("", response_model=VectorStoreResponse, status_code=201)
async def create_vector_store_route(
    body: CreateVectorStoreRequest,
    session: AsyncSession = Depends(get_session),
) -> VectorStoreResponse:
    """Create a new vector store in OpenAI and save to DB."""
    try:
        result = await create_vector_store(body.name)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"OpenAI API error: {exc}")

    store = await VectorStoreRepository(session).create(
        openai_vector_store_id=result["id"],
        name=body.name,
        status=result["status"],
    )
    return _store_to_response(store)


@router.get("/{store_id}", response_model=VectorStoreResponse)
async def get_vector_store(
    store_id: str,
    session: AsyncSession = Depends(get_session),
) -> VectorStoreResponse:
    """Return vector store detail, refreshing status from OpenAI."""
    repo = VectorStoreRepository(session)
    store = await repo.get_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Vector store not found")

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

    return _store_to_response(store)


@router.post("/{store_id}/files", response_model=VectorStoreResponse)
async def upload_file_route(
    store_id: str,
    session: AsyncSession = Depends(get_session),
    file: UploadFile = File(...),
) -> VectorStoreResponse:
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
            store.openai_vector_store_id,
            str(temp_path),
            file.filename or temp_name,
        )
        store = await repo.update(store_id, file_count=store.file_count + 1)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Upload failed: {exc}")
    finally:
        temp_path.unlink(missing_ok=True)

    return _store_to_response(store)


@router.delete("/{store_id}", status_code=204)
async def delete_vector_store_route(
    store_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a vector store from OpenAI and DB."""
    repo = VectorStoreRepository(session)
    store = await repo.get_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Vector store not found")

    await delete_vector_store(store.openai_vector_store_id)
    await repo.delete(store_id)
