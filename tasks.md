# Tasks — ai-eval Implementation

## M1 — Foundation

- [ ] T1: Project scaffolding — pyproject.toml, package structure, .gitignore
- [ ] T2: FastAPI app factory, config (Pydantic Settings), CORS middleware
- [ ] T3: SQLAlchemy models, async session, Alembic setup + initial migration
- [ ] T4: Repositories (data access layer for all entities)
- [ ] T5: React scaffolding — Vite + TypeScript + Tailwind + Shadcn/ui + React Router
- [ ] T6: App layout component (sidebar, main content area) with dark theme
- [ ] T7: Dockerfile (multi-stage build) + docker-compose.yml + entrypoint script
- [ ] T8: Dashboard page (/) — React component + API endpoint
- [ ] T9: Backend test infrastructure — pytest fixtures, conftest.py, in-memory SQLite
- [ ] T10: Frontend test infrastructure — Playwright config + smoke test

## M2 — Core CRUD

- [ ] T11: EvalConfig CRUD — API endpoints (JSON) + Pydantic schemas
- [ ] T12: EvalConfig React pages — list, create, edit, detail
- [ ] T13: Dataset upload — API endpoints + CSV parser
- [ ] T14: Dataset React pages — list, upload, preview, delete
- [ ] T15: Vector store management — service + API endpoints
- [ ] T16: Vector store React pages — create, upload files, list, delete
- [ ] T17: Backend tests for M2 — API endpoint tests for configs, datasets, vector stores
- [ ] T18: Playwright tests for M2 — CRUD flows for configs, datasets, vector stores

## M3 — Eval Engine

- [ ] T19: OpenAI provider (base LLMProvider ABC + OpenAI Responses API implementation)
- [ ] T20: OpenAI client service (thin wrapper used by eval runner)
- [ ] T21: Eval runner — background task with async parallel execution, progress tracking
- [ ] T22: Backend tests for M3 — eval runner tests with mocked OpenAI

## M4 — Comparers

- [ ] T23: Comparer base class, registry, entry-point discovery
- [ ] T24: Built-in comparers — exact_match, pattern_match, json_schema_match
- [ ] T25: Built-in comparers — semantic_similarity, llm_judge (OpenAI-dependent)
- [ ] T26: Backend tests for M4 — unit tests for all 5 comparers

## M5 — Results & Polish

- [ ] T27: Run CRUD — API endpoints (new run form data, list runs, start run)
- [ ] T28: Run React pages — new run form, run list
- [ ] T29: Run detail page — summary stats, live progress (polling), results table, failures filter
- [ ] T30: Run comparison view — side-by-side two runs
- [ ] T31: Backend tests for M5 — run API endpoint tests
- [ ] T32: Playwright tests for M5 — run creation, progress polling, results inspection, comparison

## M6 — Release

- [ ] T33: README with quickstart (docker compose up)
- [ ] T34: CONTRIBUTING.md update for React + Python workflow
- [ ] T35: Comparer plugin development guide
- [ ] T36: CI pipeline — lint (ruff + eslint), test (pytest + playwright), docker build
