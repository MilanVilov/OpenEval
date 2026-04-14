"""Pydantic schemas for Container endpoints."""

from pydantic import BaseModel, Field


class CreateContainerRequest(BaseModel):
    """Request body for creating a container."""

    name: str
    expires_after_minutes: int = Field(
        default=20,
        ge=1,
        le=20,
        description="Idle timeout in minutes (1-20). Timer resets on each use.",
    )


class ContainerResponse(BaseModel):
    """Response model for a container."""

    id: str
    openai_container_id: str
    name: str
    file_count: int
    status: str
    created_at: str

    model_config = {"from_attributes": True}
