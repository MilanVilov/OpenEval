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
    """Response model for dataset detail with all rows."""

    id: str
    name: str
    file_path: str
    row_count: int
    columns: list
    created_at: str
    rows: list[dict]

    model_config = {"from_attributes": True}


class UpdateRowsRequest(BaseModel):
    """Request body for updating dataset rows."""

    rows: list[dict]
