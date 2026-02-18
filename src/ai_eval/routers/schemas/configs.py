"""Pydantic schemas for EvalConfig endpoints."""

from pydantic import BaseModel


class CreateConfigRequest(BaseModel):
    """Request body for creating an eval configuration."""

    name: str
    system_prompt: str
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int | None = None
    tools: list[str] = []
    tool_options: dict = {}
    comparer_type: str
    comparer_config: dict = {}
    concurrency: int = 5


class UpdateConfigRequest(BaseModel):
    """Request body for updating an eval configuration."""

    name: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[str] | None = None
    tool_options: dict | None = None
    comparer_type: str | None = None
    comparer_config: dict | None = None
    concurrency: int | None = None


class ConfigResponse(BaseModel):
    """Response model for an eval configuration."""

    id: str
    name: str
    system_prompt: str
    model: str
    temperature: float
    max_tokens: int | None
    tools: list
    tool_options: dict
    comparer_type: str
    comparer_config: dict
    concurrency: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
