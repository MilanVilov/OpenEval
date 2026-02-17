"""Pydantic schemas for EvalRun endpoints."""

from pydantic import BaseModel


class CreateRunRequest(BaseModel):
    """Request body for starting an eval run."""

    eval_config_id: str
    dataset_id: str


class RunResponse(BaseModel):
    """Response model for an eval run."""

    id: str
    eval_config_id: str
    dataset_id: str
    status: str
    progress: int
    total_rows: int
    summary: dict | None
    started_at: str | None
    completed_at: str | None
    created_at: str
    config_name: str | None = None
    dataset_name: str | None = None

    model_config = {"from_attributes": True}


class RunProgressResponse(BaseModel):
    """Response model for run progress polling."""

    status: str
    progress: int
    total_rows: int
    summary: dict | None = None


class ResultResponse(BaseModel):
    """Response model for an individual eval result."""

    id: str
    eval_run_id: str
    row_index: int
    input_data: str
    expected_output: str
    actual_output: str | None
    comparer_score: float | None
    comparer_details: dict | None
    passed: bool | None
    latency_ms: int | None
    token_usage: dict | None
    error: str | None
    created_at: str

    model_config = {"from_attributes": True}


class CompareResponse(BaseModel):
    """Response model for comparing two runs."""

    run_a: RunResponse | None
    run_b: RunResponse | None
    results_a: list[ResultResponse]
    results_b: list[ResultResponse]
