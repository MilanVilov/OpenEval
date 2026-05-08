"""Pydantic schemas for remote data source and import preset endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


AuthType = Literal["none", "bearer", "basic", "header_set"]
PaginationMode = Literal["none", "page", "offset", "next_token"]
RequestMethod = Literal["GET", "POST"]


class DataSourceCreateRequest(BaseModel):
    """Request body for creating a remote data source."""

    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    method: RequestMethod = "GET"
    auth_type: AuthType = "none"
    query_params: dict[str, str] = Field(default_factory=dict)
    request_body: dict | list | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    bearer_token: str | None = None
    basic_username: str | None = None
    basic_password: str | None = None
    secret_headers: dict[str, str] = Field(default_factory=dict)
    pagination_mode: PaginationMode = "none"
    pagination_config: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self) -> "DataSourceCreateRequest":
        """Validate method and auth-specific fields."""
        if self.method == "GET" and self.request_body is not None:
            raise ValueError("GET data sources cannot define a request body")
        if self.auth_type == "bearer" and not self.bearer_token:
            raise ValueError("Bearer authentication requires bearer_token")
        if self.auth_type == "basic" and (
            not self.basic_username or not self.basic_password
        ):
            raise ValueError(
                "Basic authentication requires basic_username and basic_password",
            )
        return self


class DataSourceUpdateRequest(BaseModel):
    """Request body for updating a remote data source."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    method: RequestMethod | None = None
    auth_type: AuthType | None = None
    query_params: dict[str, str] | None = None
    request_body: dict | list | None = None
    headers: dict[str, str] | None = None
    bearer_token: str | None = None
    basic_username: str | None = None
    basic_password: str | None = None
    secret_headers: dict[str, str] | None = None
    pagination_mode: PaginationMode | None = None
    pagination_config: dict | None = None


class DataSourceResponse(BaseModel):
    """Response model for a remote data source."""

    id: str
    name: str
    url: str
    method: str
    auth_type: str
    pagination_mode: str
    has_secret_credentials: bool
    secret_header_names: list[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class DataSourceDetailResponse(DataSourceResponse):
    """Detailed response model for a remote data source."""

    query_params: dict[str, str]
    request_body: dict | list | None
    headers: dict[str, str]
    pagination_config: dict


class ImportPresetCreateRequest(BaseModel):
    """Request body for creating an import preset."""

    name: str = Field(min_length=1, max_length=255)
    records_path: str = Field(min_length=1, max_length=1024)
    field_mapping: dict[str, str]

    @model_validator(mode="after")
    def validate_mapping(self) -> "ImportPresetCreateRequest":
        """Require the dataset mapping contract for new presets."""
        _validate_field_mapping(self.field_mapping)
        return self


class ImportPresetUpdateRequest(BaseModel):
    """Request body for updating an import preset."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    records_path: str | None = Field(default=None, min_length=1, max_length=1024)
    field_mapping: dict[str, str] | None = None

    @model_validator(mode="after")
    def validate_mapping(self) -> "ImportPresetUpdateRequest":
        """Validate field mapping when it is provided."""
        if self.field_mapping is not None:
            _validate_field_mapping(self.field_mapping)
        return self


class ImportPresetResponse(BaseModel):
    """Response model for an import preset."""

    id: str
    data_source_id: str
    name: str
    records_path: str
    field_mapping: dict[str, str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ExploreDataSourceRequest(BaseModel):
    """Request body for exploring a single page from a remote data source."""

    preset_id: str | None = None
    records_path: str | None = None
    field_mapping: dict[str, str] | None = None
    page_state: dict[str, object] | None = None

    @model_validator(mode="after")
    def validate_mapping(self) -> "ExploreDataSourceRequest":
        """Validate a draft field mapping when it is present."""
        if self.field_mapping is not None:
            _validate_field_mapping(self.field_mapping)
        return self


class ExploreDataSourceResponse(BaseModel):
    """Response model for a data source explore result."""

    request_summary: dict[str, object]
    raw_response: object
    candidate_array_paths: list[str]
    field_candidates: list[str]
    records: list[object]
    mapped_rows: list[dict[str, str]]
    current_page_state: dict[str, object] | None
    next_page_state: dict[str, object] | None
    previous_page_state: dict[str, object] | None


class ImportDatasetFromSourceRequest(BaseModel):
    """Request body for creating a dataset from selected remote records."""

    name: str = Field(min_length=1, max_length=255)
    preset_id: str | None = None
    data_source_id: str | None = None
    records_path: str | None = None
    field_mapping: dict[str, str] | None = None
    selected_records: list[object]

    @model_validator(mode="after")
    def validate_rows(self) -> "ImportDatasetFromSourceRequest":
        """Require at least one selected source row."""
        if not self.selected_records:
            raise ValueError("Select at least one row to import")
        if self.preset_id is None:
            if not self.data_source_id or not self.records_path or self.field_mapping is None:
                raise ValueError(
                    "Import requires either preset_id or data_source_id, records_path, and field_mapping",
                )
            _validate_field_mapping(self.field_mapping)
        return self


class AppendDatasetFromSourceRequest(BaseModel):
    """Request body for appending selected remote records into a dataset."""

    selected_records: list[object]

    @model_validator(mode="after")
    def validate_rows(self) -> "AppendDatasetFromSourceRequest":
        """Require at least one selected source row."""
        if not self.selected_records:
            raise ValueError("Select at least one row to import")
        return self


def _validate_field_mapping(field_mapping: dict[str, str]) -> None:
    """Validate the dataset mapping contract."""
    if "input" not in field_mapping or "expected_output" not in field_mapping:
        raise ValueError("Field mapping must include input and expected_output")
    for key, value in field_mapping.items():
        if not key or not value:
            raise ValueError("Field mapping keys and values must be non-empty")
