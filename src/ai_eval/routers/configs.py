"""EvalConfig CRUD routes — JSON API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.db.repositories import ConfigRepository
from ai_eval.db.session import get_session
from ai_eval.routers.schemas.configs import (
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
        comparer_type=config.comparer_type,
        comparer_config=config.comparer_config,
        concurrency=config.concurrency,
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
        comparer_type=body.comparer_type,
        comparer_config=body.comparer_config,
        concurrency=body.concurrency,
    )
    return _config_to_response(config)


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


@router.delete("/{config_id}", status_code=204)
async def delete_config(
    config_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an evaluation configuration."""
    deleted = await ConfigRepository(session).delete(config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Configuration not found")
