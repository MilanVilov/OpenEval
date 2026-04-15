# AGENTS.md — AI Agent Instructions for OpenEval

## Overview

This file guides AI coding agents (Copilot, Cursor, Codex, etc.) working in this repository.

## Skills

**Before implementing any feature, always check the `skills/` directory for relevant guidance.**

Skills are authoritative reference documents that define conventions, patterns, and standards for this project. They MUST be followed when their domain applies.

| Skill | File | When to use |
|-------|------|-------------|
| UI Design | `skills/ui-design.md` | Tailwind theme, Shadcn/ui components, design tokens |
| Python Code Quality | `skills/python-code-quality.md` | All Python code: functions, classes, architecture, testing |
| KISS & YAGNI | `skills/kiss-yagni.md` | All code and architecture decisions: simplicity, no speculative features |
| API & Routing | `skills/api-routing.md` | FastAPI JSON API, React Router, URL design |
| Git Workflow | `skills/git-workflow.md` | Commits, branches, PRs, .gitignore |
| Testing Strategy | `skills/testing-strategy.md` | Writing tests: what to test, mocking, fixtures, assertions |
| Frontend Conventions | `skills/frontend-conventions.md` | React components, TypeScript, hooks, Shadcn/ui patterns |

## Project Context

OpenEval is an open-source AI prompt & tool evaluation framework. See `PRD.md` for the full product requirements.

### Tech Stack

- **Language**: Python 3.12+ (backend), TypeScript 5+ (frontend)
- **Backend**: FastAPI + SQLAlchemy (async) + SQLite + Alembic
- **Frontend**: React 18+ (Vite + TypeScript) + Shadcn/ui + Tailwind CSS
- **Routing**: React Router v6 (client-side), FastAPI (API)
- **Data Fetching**: Plain fetch + useState/useEffect
- **OpenAI**: Responses API via `openai` Python SDK
- **Package managers**: uv (Python), npm (frontend)
- **Testing**: pytest + pytest-asyncio (backend), Playwright (frontend E2E)
- **Container**: Docker (multi-stage build)

### Architecture Rules

- All API endpoints return JSON via Pydantic response models. Never return HTML from the backend.
- API endpoints are prefixed with `/api/`.
- Frontend is a separate Vite/React app in `frontend/`.
- React components use Shadcn/ui primitives and Tailwind for styling.
- All comparers inherit from `BaseComparer` in `src/comparers/base.py` and register via `@register_comparer` decorator.
- New comparers can also register via Python entry points (group name `open_eval.comparers`).
- OpenAI interaction is isolated in `src/services/openai_client.py` and `src/providers/openai.py`.
- All database access goes through `src/db/repositories.py`, not direct queries in routers.
- Configuration is via environment variables loaded by Pydantic Settings in `src/config.py`.
- Background tasks (eval runs) use FastAPI `BackgroundTasks` with `asyncio.Semaphore` for concurrency control.

### Code Conventions

- Use `async def` for all route handlers and service methods that do I/O.
- Type hints on all function signatures.
- Docstrings on all public classes and functions.
- Tests go in `tests/` mirroring the `src/` structure.
- Use `uv` for Python deps, `npm` for frontend deps.
- TypeScript: strict mode, no `any`, prefer `interface` over `type` for object shapes.
- React: functional components only, named exports, one component per file.
- Tests must be written alongside every feature — no feature is complete without tests.

### File Structure

```
openeval/
├── AGENTS.md
├── PRD.md
├── skills/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── alembic/
├── src/                    # Python backend
├── frontend/             # React frontend
│   ├── src/
│   ├── e2e/              # Playwright tests
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
└── tests/                # Python backend tests
```

### Key Principles

1. **Modularity**: every component (comparers, providers, parsers) has a base class + registry pattern.
2. **No auth**: single shared app, anyone with network access can use it.
3. **Docker-first**: the app must always build and run via `docker compose up`.
4. **Skills are law**: when a skill document covers a topic, follow it precisely.
5. **Test-driven**: every feature ships with tests.
