"""Pydantic schemas for Dataset endpoints."""

from pydantic import BaseModel


class DatasetResponse(BaseModel):
    """Response model for a dataset."""

    id: str
    name: str
    file_path: str
    row_count: int
    columns: list
    created_at: str

    model_config = {"from_attributes": True}


class DatasetDetailResponse(BaseModel):
    """Response model for dataset detail with preview rows."""

    id: str
    name: str
    file_path: str
    row_count: int
    columns: list
    created_at: str
    preview: list[dict]

    model_config = {"from_attributes": True}
