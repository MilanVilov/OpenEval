"""Container management routes — JSON API."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.config import get_settings
from ai_eval.db.repositories import ContainerRepository
from ai_eval.db.session import get_session
from ai_eval.routers.schemas.containers import (
    ContainerResponse,
    CreateContainerRequest,
)
from ai_eval.services.openai_client import (
    create_container,
    delete_container,
    get_container_info,
    upload_file_to_container,
)

router = APIRouter(prefix="/api/containers", tags=["containers"])


def _container_to_response(container: object) -> ContainerResponse:
    """Convert a Container ORM object to a ContainerResponse."""
    return ContainerResponse(
        id=container.id,
        openai_container_id=container.openai_container_id,
        name=container.name,
        file_count=container.file_count,
        status=container.status,
        created_at=str(container.created_at),
    )


@router.get("", response_model=list[ContainerResponse])
async def list_containers(
    session: AsyncSession = Depends(get_session),
) -> list[ContainerResponse]:
    """List all containers."""
    containers = await ContainerRepository(session).list_all()
    return [_container_to_response(c) for c in containers]


@router.post("", response_model=ContainerResponse, status_code=201)
async def create_container_route(
    body: CreateContainerRequest,
    session: AsyncSession = Depends(get_session),
) -> ContainerResponse:
    """Create a new container in OpenAI and save to DB."""
    try:
        result = await create_container(body.name)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"OpenAI API error: {exc}")

    container = await ContainerRepository(session).create(
        openai_container_id=result["id"],
        name=body.name,
        status=result["status"],
    )
    return _container_to_response(container)


@router.get("/{container_id}", response_model=ContainerResponse)
async def get_container(
    container_id: str,
    session: AsyncSession = Depends(get_session),
) -> ContainerResponse:
    """Return container detail, refreshing status from OpenAI."""
    repo = ContainerRepository(session)
    container = await repo.get_by_id(container_id)
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    try:
        info = await get_container_info(container.openai_container_id)
        updates: dict = {}
        if info["status"] != container.status:
            updates["status"] = info["status"]
        if updates:
            container = await repo.update(container_id, **updates)
    except Exception:
        pass  # Show stale data if OpenAI is unreachable

    return _container_to_response(container)


@router.post("/{container_id}/files", response_model=ContainerResponse)
async def upload_file_route(
    container_id: str,
    session: AsyncSession = Depends(get_session),
    file: UploadFile = File(...),
) -> ContainerResponse:
    """Upload a file to a container."""
    repo = ContainerRepository(session)
    container = await repo.get_by_id(container_id)
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    settings = get_settings()
    temp_name = f"{uuid4().hex}_{file.filename}"
    temp_path = Path(settings.upload_dir) / temp_name

    content = await file.read()
    temp_path.write_bytes(content)

    try:
        await upload_file_to_container(
            container.openai_container_id,
            str(temp_path),
            file.filename or temp_name,
        )
        container = await repo.update(container_id, file_count=container.file_count + 1)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Upload failed: {exc}")
    finally:
        temp_path.unlink(missing_ok=True)

    return _container_to_response(container)


@router.delete("/{container_id}", status_code=204)
async def delete_container_route(
    container_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete a container from OpenAI and DB."""
    repo = ContainerRepository(session)
    container = await repo.get_by_id(container_id)
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    await delete_container(container.openai_container_id)
    await repo.delete(container_id)
