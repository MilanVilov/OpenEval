"""EvalConfig CRUD routes — JSON API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories import ConfigRepository
from src.db.session import get_session
from src.routers.schemas.configs import (
    ConfigResponse,
    CreateConfigRequest,
    UpdateConfigRequest,
)

router = APIRouter(prefix="/api/configs", tags=["configs"])


def _config_to_response(config: object) -> ConfigResponse:
    """Convert an EvalConfig ORM object to a ConfigResponse."""
    return ConfigResponse(
        id=config.id,
        name=config.name,
        system_prompt=config.system_prompt,
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        tools=config.tools,
        tool_options=config.tool_options,
        graders=config.graders or [],
        tags=config.tags or [],
        concurrency=config.concurrency,
        readonly=config.readonly,
        reasoning_config=config.reasoning_config,
        response_format=config.response_format,
        created_at=str(config.created_at),
        updated_at=str(config.updated_at),
    )


@router.get("", response_model=list[ConfigResponse])
async def list_configs(
    session: AsyncSession = Depends(get_session),
) -> list[ConfigResponse]:
    """List all eval configurations."""
    configs = await ConfigRepository(session).list_all()
    return [_config_to_response(c) for c in configs]


@router.post("", response_model=ConfigResponse, status_code=201)
async def create_config(
    body: CreateConfigRequest,
    session: AsyncSession = Depends(get_session),
) -> ConfigResponse:
    """Create a new evaluation configuration."""
    config = await ConfigRepository(session).create(
        name=body.name,
        system_prompt=body.system_prompt,
        model=body.model,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
        tools=body.tools,
        tool_options=body.tool_options,
        graders=[g.model_dump() for g in body.graders],
        tags=body.tags,
        concurrency=body.concurrency,
        readonly=body.readonly,
        reasoning_config=body.reasoning_config,
        response_format=body.response_format,
    )
    return _config_to_response(config)


@router.get("/tags", response_model=list[str])
async def list_tags(
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    """Return a deduplicated, sorted list of all tags used across configs."""
    configs = await ConfigRepository(session).list_all()
    tags: set[str] = set()
    for c in configs:
        for t in c.tags or []:
            tags.add(t)
    return sorted(tags)


@router.get("/{config_id}", response_model=ConfigResponse)
async def get_config(
    config_id: str,
    session: AsyncSession = Depends(get_session),
) -> ConfigResponse:
    """Return a single eval configuration."""
    config = await ConfigRepository(session).get_by_id(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return _config_to_response(config)


@router.put("/{config_id}", response_model=ConfigResponse)
async def update_config(
    config_id: str,
    body: UpdateConfigRequest,
    session: AsyncSession = Depends(get_session),
) -> ConfigResponse:
    """Update an existing evaluation configuration."""
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=422, detail="No fields to update")
    config = await ConfigRepository(session).update(config_id, **fields)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return _config_to_response(config)


@router.post("/{config_id}/duplicate", response_model=ConfigResponse, status_code=201)
async def duplicate_config(
    config_id: str,
    session: AsyncSession = Depends(get_session),
) -> ConfigResponse:
    """Duplicate an existing evaluation configuration."""
    repo = ConfigRepository(session)
    original = await repo.get_by_id(config_id)
    if not original:
        raise HTTPException(status_code=404, detail="Configuration not found")
    copy = await repo.create(
        name=f"{original.name} copy",
        system_prompt=original.system_prompt,
        model=original.model,
        temperature=original.temperature,
        max_tokens=original.max_tokens,
        tools=original.tools,
        tool_options=original.tool_options,
        graders=original.graders or [],
        tags=original.tags or [],
        concurrency=original.concurrency,
        readonly=False,
        reasoning_config=original.reasoning_config,
        response_format=original.response_format,
    )
    return _config_to_response(copy)


@router.delete("/{config_id}", status_code=204)
async def delete_config(
    config_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an evaluation configuration."""
    deleted = await ConfigRepository(session).delete(config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Configuration not found")
