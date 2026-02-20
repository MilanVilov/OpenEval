"""Pydantic schemas for the AI schema generation endpoint."""

from pydantic import BaseModel


class GenerateSchemaRequest(BaseModel):
    """Request body for AI-powered JSON schema generation."""

    description: str


class GenerateSchemaResponse(BaseModel):
    """Response body with generated JSON schema."""

    schema_name: str
    schema_body: dict
