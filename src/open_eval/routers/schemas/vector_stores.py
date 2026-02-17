"""Pydantic schemas for VectorStore endpoints."""

from pydantic import BaseModel


class CreateVectorStoreRequest(BaseModel):
    """Request body for creating a vector store."""

    name: str


class VectorStoreResponse(BaseModel):
    """Response model for a vector store."""

    id: str
    openai_vector_store_id: str
    name: str
    file_count: int
    status: str
    created_at: str

    model_config = {"from_attributes": True}
