"""Pydantic schemas for EvalConfig endpoints."""

from typing import Literal

from pydantic import BaseModel, field_validator, model_validator


GraderType = Literal[
    "prompt",
    "string_check",
    "python",
    "semantic_similarity",
    "json_schema",
    "json_field",
]


class GraderSchema(BaseModel):
    """Schema for a single grader.

    The ``type`` field selects the grader kind:

    * ``prompt`` — LLM-based evaluation using a user-defined prompt.
    * ``string_check`` — deterministic string comparison (equals, contains, …).
    * ``python`` — execute a user-supplied ``grade(sample, item)`` function.
    * ``semantic_similarity`` — cosine similarity via OpenAI embeddings.
    * ``json_schema`` — validate JSON structure and key values.
    * ``json_field`` — extract and compare a named field from JSON output.

    Fields are type-dependent; unused fields may be ``None``.
    """

    name: str
    type: GraderType = "prompt"

    # --- Prompt grader fields ---
    prompt: str | None = None
    model: str | None = None

    # --- String check grader fields ---
    input_value: str | None = None
    operation: str | None = None
    reference_value: str | None = None

    # --- Python grader fields ---
    source_code: str | None = None

    # --- Semantic similarity fields ---
    # Uses threshold (shared) and optionally model

    # --- JSON schema fields ---
    strict: bool | None = None

    # --- JSON field fields ---
    field_name: str | None = None
    case_sensitive: bool | None = None
    strip_whitespace: bool | None = None

    # --- Shared ---
    threshold: float | None = None
    weight: float = 1.0

    @field_validator("weight")
    @classmethod
    def _validate_weight(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError(f"Weight must be between 0 and 1, got {v}")
        return v

    @model_validator(mode="after")
    def _apply_type_defaults(self) -> "GraderSchema":
        """Apply per-type threshold defaults when not explicitly set."""
        if self.threshold is None:
            _type_thresholds = {
                "semantic_similarity": 0.8,
                "json_schema": 1.0,
            }
            self.threshold = _type_thresholds.get(self.type, 0.7)
        return self


class CreateConfigRequest(BaseModel):
    """Request body for creating an eval configuration."""

    name: str
    system_prompt: str
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int | None = None
    tools: list[str] = []
    tool_options: dict = {}
    graders: list[GraderSchema] = []
    tags: list[str] = []
    concurrency: int = 5
    readonly: bool = False
    reasoning_config: dict | None = None
    response_format: dict | None = None

    @field_validator("graders")
    @classmethod
    def _validate_graders(cls, v: list[GraderSchema]) -> list[GraderSchema]:
        if len(v) == 0:
            raise ValueError("At least one grader is required")
        names = [g.name for g in v]
        if len(names) != len(set(names)):
            raise ValueError("Grader names must be unique")
        return v


class UpdateConfigRequest(BaseModel):
    """Request body for updating an eval configuration."""

    name: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[str] | None = None
    tool_options: dict | None = None
    graders: list[GraderSchema] | None = None
    tags: list[str] | None = None
    concurrency: int | None = None
    readonly: bool | None = None
    reasoning_config: dict | None = None
    response_format: dict | None = None


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
    graders: list[dict] = []
    tags: list[str] = []
    concurrency: int
    readonly: bool = False
    reasoning_config: dict | None = None
    response_format: dict | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
