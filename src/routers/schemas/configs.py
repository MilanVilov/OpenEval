"""Pydantic schemas for EvalConfig endpoints."""

from pydantic import BaseModel, field_validator


class CustomGraderSchema(BaseModel):
    """Schema for a single custom grader.

    The ``type`` field selects the grader kind:

    * ``prompt`` — LLM-based evaluation using a user-defined prompt.
    * ``string_check`` — deterministic string comparison (equals, contains, …).
    * ``python`` — execute a user-supplied ``grade(sample, item)`` function.

    Fields are type-dependent; unused fields may be ``None``.
    """

    name: str
    type: str = "prompt"

    # --- Prompt grader fields ---
    prompt: str | None = None
    model: str | None = None

    # --- String check grader fields ---
    input_value: str | None = None
    operation: str | None = None
    reference_value: str | None = None

    # --- Python grader fields ---
    source_code: str | None = None

    # --- Shared ---
    threshold: float = 0.7


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
    custom_graders: list[CustomGraderSchema] = []
    comparer_weights: dict[str, float] = {}
    tags: list[str] = []
    concurrency: int = 5
    readonly: bool = False
    reasoning_config: dict | None = None
    response_format: dict | None = None

    @field_validator("comparer_weights")
    @classmethod
    def _validate_weights(cls, v: dict[str, float]) -> dict[str, float]:
        for key, weight in v.items():
            if not 0 <= weight <= 1:
                raise ValueError(f"Weight for '{key}' must be between 0 and 1, got {weight}")
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
    comparer_type: str | None = None
    comparer_config: dict | None = None
    custom_graders: list[CustomGraderSchema] | None = None
    comparer_weights: dict[str, float] | None = None
    tags: list[str] | None = None
    concurrency: int | None = None
    readonly: bool | None = None
    reasoning_config: dict | None = None
    response_format: dict | None = None

    @field_validator("comparer_weights")
    @classmethod
    def _validate_weights(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        if v is None:
            return v
        for key, weight in v.items():
            if not 0 <= weight <= 1:
                raise ValueError(f"Weight for '{key}' must be between 0 and 1, got {weight}")
        return v


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
    custom_graders: list[dict] = []
    comparer_weights: dict[str, float] = {}
    tags: list[str] = []
    concurrency: int
    readonly: bool = False
    reasoning_config: dict | None = None
    response_format: dict | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
