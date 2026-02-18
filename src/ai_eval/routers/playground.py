"""Playground route — manually test a config with a single message."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.db.repositories import ConfigRepository
from ai_eval.db.session import get_session
from ai_eval.providers.openai import OpenAIProvider
from ai_eval.routers.schemas.playground import PlaygroundRequest, PlaygroundResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/playground", tags=["playground"])


@router.post("", response_model=PlaygroundResponse)
async def run_playground(
    body: PlaygroundRequest,
    session: AsyncSession = Depends(get_session),
) -> PlaygroundResponse:
    """Send a single message using a config and return the full OpenAI response."""
    config = await ConfigRepository(session).get_by_id(body.config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    provider = OpenAIProvider()
    result = await provider.generate(
        system_prompt=config.system_prompt,
        user_input=body.message,
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        tools=config.tools or [],
        tool_options=config.tool_options or {},
        reasoning_config=config.reasoning_config,
        response_format=config.response_format,
    )

    return PlaygroundResponse(
        text=result.text,
        latency_ms=result.latency_ms,
        token_usage=result.token_usage,
        raw_response=result.raw_response or {},
    )
