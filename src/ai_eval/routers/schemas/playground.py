"""Pydantic schemas for Playground endpoint."""

from pydantic import BaseModel


class PlaygroundRequest(BaseModel):
    """Request body for the playground endpoint."""

    config_id: str
    message: str


class PlaygroundResponse(BaseModel):
    """Full response from a playground invocation."""

    text: str
    latency_ms: int
    token_usage: dict
    raw_response: dict
