# Tasks — ai-eval Implementation

## M1 — Foundation

- [x] T1: Project scaffolding — pyproject.toml, package structure, .gitignore ✅
- [x] T2: FastAPI app factory, config (Pydantic Settings), static/template mount ✅
- [x] T3: SQLAlchemy models, async session, Alembic setup + initial migration ✅
- [x] T4: Repositories (data access layer for all entities) ✅
- [x] T5: Base Jinja2 layout (base.html, sidebar, CSS with dark midnight theme) ✅
- [x] T6: Dockerfile + docker-compose.yml + entrypoint script ✅
- [x] T7: Dashboard page (/) ✅

## M2 — Core CRUD

- [x] T8: EvalConfig CRUD — router + templates (list, create, edit, delete) ✅
- [x] T9: Dataset upload — router + CSV parser + templates (list, upload, preview, delete) ✅
- [x] T10: Vector store management — service + router + templates (create, upload files, list, delete) ✅

## M3 — Eval Engine

- [x] T11: OpenAI provider (base LLMProvider ABC + OpenAI Responses API implementation) ✅
- [x] T12: OpenAI client service (thin wrapper used by eval runner) ✅
- [x] T13: Eval runner — background task with async parallel execution, progress tracking ✅

## M4 — Comparers

- [x] T14: Comparer base class, registry, entry-point discovery ✅
- [x] T15: Built-in comparers — exact_match, pattern_match, json_schema_match ✅
- [x] T16: Built-in comparers — semantic_similarity, llm_judge (OpenAI-dependent) ✅

## M5 — Results & Polish

- [x] T17: Run CRUD — router + templates (new run form, list runs, start run) ✅
- [x] T18: Run detail page — summary stats, live progress, results table, failures filter ✅
- [x] T19: Run comparison view — side-by-side two runs ✅

## M6 — Release

- [x] T20: README, CONTRIBUTING.md, LICENSE, plugin dev guide ✅
