# AGENTS.md — AI Agent Instructions for ai-eval

## Overview

This file guides AI coding agents (Copilot, Cursor, Codex, etc.) working in this repository.

## Skills

**Before implementing any feature, always check the `skills/` directory for relevant guidance.**

Skills are authoritative reference documents that define conventions, patterns, and standards for this project. They MUST be followed when their domain applies.

| Skill | File | When to use |
|-------|------|-------------|
| UI Design | `skills/ui-design.md` | Any frontend work: templates, CSS, HTML, components |
| Python Code Quality | `skills/python-code-quality.md` | All Python code: functions, classes, architecture, testing |
| KISS & YAGNI | `skills/kiss-yagni.md` | All code and architecture decisions: simplicity, no speculative features |
| API & Routing | `skills/api-routing.md` | FastAPI routers, endpoints, HTMX interactions, URL design |
| Git Workflow | `skills/git-workflow.md` | Commits, branches, PRs, .gitignore |
| Testing Strategy | `skills/testing-strategy.md` | Writing tests: what to test, mocking, fixtures, assertions |

## Project Context

ai-eval is an open-source AI prompt & tool evaluation framework. See `PRD.md` for the full product requirements.

### Tech Stack

- **Language**: Python 3.12+
- **Backend**: FastAPI + SQLAlchemy (async) + SQLite + Alembic
- **Frontend**: Jinja2 templates + HTMX + Alpine.js
- **OpenAI**: Responses API via `openai` Python SDK
- **Package manager**: uv
- **Container**: Docker

### Architecture Rules

- All comparers inherit from `BaseComparer` in `src/ai_eval/comparers/base.py` and register via `@register_comparer` decorator.
- New comparers can also register via Python entry points under `ai_eval.comparers`.
- OpenAI interaction is isolated in `src/ai_eval/services/openai_client.py` and `src/ai_eval/providers/openai.py`.
- All database access goes through `src/ai_eval/db/repositories.py`, not direct queries in routers.
- Configuration is via environment variables loaded by Pydantic Settings in `src/ai_eval/config.py`.
- Background tasks (eval runs) use FastAPI `BackgroundTasks` with `asyncio.Semaphore` for concurrency control.

### Code Conventions

- Use `async def` for all route handlers and service methods that do I/O.
- Type hints on all function signatures.
- Docstrings on all public classes and functions.
- Tests go in `tests/` mirroring the `src/ai_eval/` structure.
- Use `uv` for dependency management (pyproject.toml, not requirements.txt).

### File Structure

```
ai-eval/
├── AGENTS.md              # This file
├── PRD.md                 # Product requirements
├── skills/                # Skill documents (MUST be consulted)
│   └── ui-design.md       # UI/CSS design system
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── alembic/
├── static/
├── templates/
├── src/ai_eval/
└── tests/
```

### Key Principles

1. **Modularity**: every component (comparers, providers, parsers) has a base class + registry pattern.
2. **No auth**: single shared app, anyone with network access can use it.
3. **Docker-first**: the app must always build and run via `docker compose up`.
4. **Skills are law**: when a skill document covers a topic, follow it precisely.
