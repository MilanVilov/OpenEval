"""Pydantic schemas for Dataset endpoints."""

from pydantic import BaseModel


class DatasetResponse(BaseModel):
    """Response model for a dataset."""

    id: str
    name: str
    file_path: str
    row_count: int
    columns: list
    import_preset_id: str | None = None
    has_import_source: bool = False
    created_at: str

    model_config = {"from_attributes": True}


class DatasetDetailResponse(BaseModel):
    """Response model for dataset detail with all rows."""

    id: str
    name: str
    file_path: str
    row_count: int
    columns: list
    import_preset_id: str | None = None
    has_import_source: bool = False
    import_source_snapshot: dict | None = None
    created_at: str
    rows: list[dict]

    model_config = {"from_attributes": True}


class UpdateRowsRequest(BaseModel):
    """Request body for updating dataset rows."""

    rows: list[dict]
