# Contributing to OpenEval

Thank you for your interest in contributing! Here's how to get started.

## Development Setup

1. Fork and clone the repository
2. Install [uv](https://astral.sh/uv): `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Install dependencies: `uv sync`
4. Set up environment: `cp .env.example .env` and add your `OPENAI_API_KEY`
5. Run migrations: `uv run alembic upgrade head`
6. Start dev server: `uv run uvicorn open_eval.app:create_app --factory --reload`

## Code Standards

- **Python 3.12+** with type hints on all signatures
- **Async/await** for all I/O operations
- **Ruff** for linting and formatting: `uv run ruff check . && uv run ruff format .`
- **Docstrings** on all public classes and functions
- Follow the skill documents in `skills/` for detailed conventions

## Branching

- `main` — stable, always deployable
- `feat/<name>` — new features
- `fix/<name>` — bug fixes

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new comparer for fuzzy matching
fix: handle empty CSV upload gracefully
docs: update README with new env vars
refactor: simplify eval runner progress tracking
```

## Testing

```bash
uv run pytest
uv run pytest tests/comparers/  # specific directory
uv run pytest -x               # stop on first failure
```

## Adding a Comparer

1. Create `src/open_eval/comparers/my_comparer.py`
2. Inherit from `BaseComparer`, use `@register_comparer("my_name")`
3. Implement `async def compare(self, *, expected, actual) -> tuple[float, bool, dict]`
4. Add entry point in `pyproject.toml` under `[project.entry-points."open_eval.comparers"]`
5. Import in `comparers/registry.py` `_ensure_builtins_imported()`
6. Add tests in `tests/comparers/`

## Pull Requests

- Keep PRs focused on a single concern
- Include tests for new features
- Run linting before submitting
- Reference any related issues

## Questions?

Open an issue on GitHub.
