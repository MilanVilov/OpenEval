# PRD: ai-eval — AI Prompt & Tool Evaluation Framework

## Overview

**ai-eval** is an open-source evaluation framework for testing AI prompt configurations with OpenAI hosted tools (file_search, shell). Users configure a prompt, attach tools, upload a CSV dataset of input/expected-output pairs, and run batch evaluations. Results are compared using pluggable comparers (exact match, semantic similarity, LLM-as-judge, pattern match, JSON schema match) and displayed in a server-rendered web dashboard.

The app is packaged as a Docker image. Run it locally or on a shared server — no user accounts, no auth. Anyone who can reach the URL can use it.

## Goals

- **Repeatable evals**: run the same dataset against different prompts/tool configs and compare results across runs.
- **Pluggable comparers**: ship 5 built-in comparers; make it trivial for contributors to add new ones.
- **OpenAI Responses API integration**: first-class support for `file_search` (including vector store creation) and `shell` hosted tools.
- **Zero-config deployment**: single `docker run` command to get started.
- **Open-source friendly**: clean module boundaries, well-documented extension points, permissive license.

## Non-Goals (v1)

- Multi-provider support (Anthropic, Google, etc.) — architecture allows it, but only OpenAI ships.
- User authentication / multi-tenancy.
- Result export (CSV/JSON).
- Cost tracking / token cost estimation.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12+ |
| Web framework | FastAPI |
| Frontend | Jinja2 templates + HTMX + Alpine.js |
| Database | SQLite via SQLAlchemy (async) + Alembic migrations |
| OpenAI SDK | `openai` Python SDK (Responses API) |
| Task runner | `asyncio` with configurable concurrency (`asyncio.Semaphore`) |
| Package manager | `uv` (with pyproject.toml) |
| Container | Docker (single-stage build) |
| Testing | pytest + pytest-asyncio |

---

## Data Model

### Entities

1. **EvalConfig** — a saved evaluation configuration
   - `id` (UUID)
   - `name` (str)
   - `system_prompt` (text)
   - `model` (str, e.g. `gpt-4.1`)
   - `temperature` (float)
   - `max_tokens` (int, optional)
   - `tools` (JSON — list of tool configs: `file_search`, `shell`, etc.)
   - `tool_options` (JSON — per-tool settings, e.g. file_search vector_store_id)
   - `comparer_type` (str — registered comparer name)
   - `comparer_config` (JSON — comparer-specific settings, e.g. similarity threshold)
   - `concurrency` (int, default 5)
   - `created_at`, `updated_at`

2. **Dataset** — an uploaded CSV file
   - `id` (UUID)
   - `name` (str)
   - `file_path` (str — path to stored CSV on disk)
   - `row_count` (int)
   - `columns` (JSON — list of column names)
   - `created_at`

3. **VectorStore** — a tracked OpenAI vector store created from the UI
   - `id` (UUID)
   - `openai_vector_store_id` (str — the `vs_xxx` ID from OpenAI)
   - `name` (str)
   - `file_count` (int)
   - `status` (str — `creating`, `ready`, `failed`)
   - `created_at`

4. **EvalRun** — a single execution of an EvalConfig against a Dataset
   - `id` (UUID)
   - `eval_config_id` (FK)
   - `dataset_id` (FK)
   - `status` (enum: `pending`, `running`, `completed`, `failed`)
   - `progress` (int — rows completed)
   - `total_rows` (int)
   - `summary` (JSON — aggregate stats: accuracy, avg latency, pass/fail counts)
   - `started_at`, `completed_at`

5. **EvalResult** — one row's result within a run
   - `id` (UUID)
   - `eval_run_id` (FK)
   - `row_index` (int)
   - `input_data` (text — the input sent)
   - `expected_output` (text)
   - `actual_output` (text — raw LLM response)
   - `comparer_score` (float, 0.0–1.0)
   - `comparer_details` (JSON — comparer-specific breakdown)
   - `passed` (bool)
   - `latency_ms` (int)
   - `token_usage` (JSON — prompt_tokens, completion_tokens)
   - `error` (text, nullable)
   - `created_at`

---

## Architecture & Module Structure

```
ai-eval/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── alembic/                    # DB migrations
├── alembic.ini
├── static/                     # CSS, JS (HTMX, Alpine.js)
├── templates/                  # Jinja2 templates
│   ├── base.html
│   ├── dashboard.html
│   ├── configs/                # eval config CRUD pages
│   ├── datasets/               # dataset upload & browse
│   ├── vector_stores/          # vector store management
│   ├── runs/                   # run list, detail, live progress
│   └── components/             # reusable HTMX partials
├── src/
│   └── ai_eval/
│       ├── __init__.py
│       ├── app.py              # FastAPI app factory
│       ├── config.py           # Settings (env vars, OpenAI key)
│       ├── db/
│       │   ├── models.py       # SQLAlchemy ORM models
│       │   ├── session.py      # async engine + session factory
│       │   └── repositories.py # data access layer
│       ├── routers/
│       │   ├── configs.py      # EvalConfig CRUD endpoints
│       │   ├── datasets.py     # Dataset upload/list endpoints
│       │   ├── vector_stores.py# Vector store CRUD + file upload
│       │   └── runs.py         # Run trigger, status, results
│       ├── services/
│       │   ├── eval_runner.py  # Orchestrates a run (parallel execution)
│       │   ├── openai_client.py# Thin wrapper around OpenAI Responses API
│       │   ├── vector_store_service.py # Create/manage OpenAI vector stores
│       │   └── dataset_parser.py # CSV parsing & validation
│       ├── comparers/
│       │   ├── base.py         # Abstract base class: Comparer
│       │   ├── registry.py     # Comparer registry (auto-discovery)
│       │   ├── exact_match.py
│       │   ├── pattern_match.py
│       │   ├── semantic_similarity.py
│       │   ├── llm_judge.py
│       │   └── json_schema_match.py
│       └── providers/          # Future: multi-provider abstraction
│           ├── base.py         # Abstract LLMProvider
│           └── openai.py       # OpenAI Responses API implementation
└── tests/
```

---

## Comparer Plugin System

All comparers inherit from an abstract base class and register via a decorator:

```python
@register_comparer("exact_match")
class ExactMatchComparer(BaseComparer):
    def compare(self, expected: str, actual: str, config: dict) -> CompareResult:
        ...
```

- **`BaseComparer`** defines: `compare(expected, actual, config) -> CompareResult` where `CompareResult` has `score: float`, `passed: bool`, `details: dict`.
- **Registry** uses Python entry points (`[project.entry-points."ai_eval.comparers"]`) so external packages can register new comparers without modifying core code.
- **Config schema**: each comparer can declare a `config_schema()` classmethod returning a JSON schema for its settings (rendered in the UI as a dynamic form).

### Built-in Comparers

| Name | Logic | Config options |
|---|---|---|
| `exact_match` | `expected.strip() == actual.strip()`, optional case-insensitive | `case_sensitive: bool` |
| `pattern_match` | Regex or substring match against actual output | `pattern: str`, `mode: regex\|substring` |
| `semantic_similarity` | Cosine similarity via OpenAI embeddings | `model: str`, `threshold: float` |
| `llm_judge` | Sends expected+actual to an LLM with a grading prompt | `judge_model: str`, `grading_prompt: str`, `pass_threshold: float` |
| `json_schema_match` | Parse actual as JSON, validate against a JSON schema | `schema: dict` |

---

## OpenAI Integration

### Responses API

Each eval row triggers a call to the OpenAI Responses API:

1. Build the request: system prompt from EvalConfig + user message from dataset row input.
2. Attach tools: `file_search` (with vector store ID from tool_options), `shell` (if enabled).
3. Send request, capture full response including tool call traces.
4. Extract final text output for comparison.
5. Record token usage and latency.

### Vector Store Management

Users can create and manage OpenAI vector stores directly from the UI:

1. **Create**: name the store → calls `openai.vector_stores.create()`.
2. **Upload files**: select files from local machine → uploaded via `openai.vector_stores.files.create()` with streaming upload.
3. **List**: see all stores tracked by the app, with file count and status.
4. **Delete**: remove from OpenAI and local tracking.
5. **Select in EvalConfig**: when configuring file_search, a dropdown lists available vector stores by name.

### Tool Configuration

- **file_search**: user picks a vector store from the UI dropdown (or pastes an ID manually). The store is attached to the Responses API call.
- **shell**: enabled/disabled toggle. Runs in OpenAI's sandbox.

---

## Web UI Pages

1. **Dashboard** (`/`) — overview: recent runs with pass rates, quick links to create config or start a run.
2. **Eval Configs** (`/configs`) — list, create, edit, delete configs. Form includes: prompt editor (textarea), model selector, tool toggles, vector store picker (for file_search), comparer picker with dynamic config form.
3. **Datasets** (`/datasets`) — upload CSV, preview first N rows, validate columns, delete.
4. **Vector Stores** (`/vector-stores`) — create new store, upload files to existing store, list all stores with status, delete.
5. **Run Eval** (`/runs/new`) — pick config + dataset, start run.
6. **Run Detail** (`/runs/{id}`) — summary banner (total accuracy %, avg request time, pass/fail count) + live progress bar (HTMX polling) + results table with filter to show **failed comparisons only** + expandable per-row detail showing actual vs expected side-by-side.
7. **Run Comparison** (`/runs/compare`) — side-by-side two runs on the same dataset.

### Run Detail — Summary Section

Displayed prominently at the top of the run detail page:

| Metric | Description |
|---|---|
| **Total Accuracy** | `passed_count / total_rows` as percentage |
| **Avg Request Time** | Mean `latency_ms` across all rows |
| **Pass / Fail Count** | e.g. "47 passed, 3 failed out of 50" |
| **Avg Comparer Score** | Mean score (useful for non-binary comparers like semantic similarity) |

Below the summary: a filterable results table. Default view shows all rows. A toggle/button to **"Show failures only"** filters to `passed=false`, making it easy to inspect what went wrong.

---

## CSV Format

Minimum required columns:

```csv
input,expected_output
"What is 2+2?","4"
"Summarize this document","The document discusses..."
```

Optional columns: `metadata` (JSON string), `tags` (comma-separated). Additional columns are preserved and stored but not used by the core eval logic.

---

## Eval Execution Flow

1. User selects config + dataset, clicks "Run".
2. Backend creates an `EvalRun` record (`status=pending`).
3. `eval_runner.py` is invoked as a background task (FastAPI `BackgroundTasks`).
4. Runner parses the dataset, creates a semaphore with configured concurrency.
5. For each row, an async task: calls OpenAI → gets response → runs comparer → writes `EvalResult`.
6. Progress is updated on `EvalRun` after each row completes.
7. UI polls `/runs/{id}/progress` via HTMX every 2s to show live progress.
8. On completion, runner computes summary stats (accuracy, avg latency, pass/fail counts) and writes them to `EvalRun.summary`.

---

## Configuration

All runtime configuration via environment variables (loaded with Pydantic Settings):

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key | (required) |
| `DATABASE_URL` | SQLite connection string | `sqlite+aiosqlite:///./data/ai_eval.db` |
| `UPLOAD_DIR` | Directory for uploaded CSVs | `./data/uploads` |
| `DEFAULT_CONCURRENCY` | Default parallel requests per run | `5` |
| `HOST` | Server bind host | `0.0.0.0` |
| `PORT` | Server bind port | `8000` |

---

## Docker Packaging

### Dockerfile

- Single-stage build based on `python:3.12-slim`.
- Install dependencies via `uv pip install`.
- Copy source, templates, static assets.
- `VOLUME /app/data` — persists SQLite DB + uploaded files across container restarts.
- `EXPOSE 8000`.
- Entrypoint: run Alembic migrations then start uvicorn.

### docker-compose.yml

```yaml
services:
  ai-eval:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ai-eval-data:/app/data
volumes:
  ai-eval-data:
```

### Usage

```bash
# Option 1: docker compose
OPENAI_API_KEY=sk-xxx docker compose up

# Option 2: docker run
docker run -p 8000:8000 -e OPENAI_API_KEY=sk-xxx -v ai-eval-data:/app/data ai-eval
```

No user accounts. Whoever can reach `http://host:8000` has full access.

---

## Extensibility Points

1. **Comparers**: entry-point based plugin system. Install a pip package that registers a comparer, restart, it appears in the UI.
2. **Providers**: `providers/base.py` defines `LLMProvider` ABC. Only OpenAI ships in v1, but the interface is ready for others.
3. **Dataset formats**: `dataset_parser.py` can be extended to support JSONL, Excel, etc.
4. **Tool adapters**: tool configuration is JSON-based, new OpenAI tools can be added without code changes.

---

## Milestones

### M1 — Foundation
- Project scaffolding (pyproject.toml, Dockerfile, FastAPI app, SQLite + Alembic)
- Data models + repositories
- Basic Jinja2 layout + static assets (HTMX, Alpine.js)
- Docker build working

### M2 — Core CRUD
- EvalConfig create/edit/list/delete with web forms
- Dataset upload (CSV), validation, preview
- Vector store create/upload-files/list/delete via OpenAI API

### M3 — Eval Engine
- OpenAI Responses API client with file_search + shell support
- Eval runner with async parallel execution
- EvalResult recording

### M4 — Comparers
- Base comparer + registry + entry-point discovery
- All 5 built-in comparers implemented
- Comparer config rendered dynamically in UI

### M5 — Results & Polish
- Run detail page with summary banner (accuracy, avg request time, pass/fail)
- Failures-only filter
- Per-row result inspection (actual vs expected side-by-side)
- Run comparison view

### M6 — Open-Source Release
- README with quickstart (docker compose up)
- CONTRIBUTING.md
- Comparer plugin development guide
- LICENSE (MIT)
- GitHub Actions CI (lint, test, docker build)
