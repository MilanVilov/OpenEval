"""Pydantic schemas for Container endpoints."""

from pydantic import BaseModel


class CreateContainerRequest(BaseModel):
    """Request body for creating a container."""

    name: str


class ContainerResponse(BaseModel):
    """Response model for a container."""

    id: str
    openai_container_id: str
    name: str
    file_count: int
    status: str
    created_at: str

    model_config = {"from_attributes": True}
