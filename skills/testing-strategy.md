# Skill: Testing Strategy — What, How, and When to Test

This skill defines testing conventions for ai-eval. All tests use pytest and follow these patterns.

---

## Test Pyramid

```
         ╱  E2E (few)  ╲        Browser-level, Docker required
        ╱ Integration    ╲      Real DB, real templates, mocked OpenAI
       ╱   Unit (most)    ╲    Pure logic, no I/O, no DB
```

| Layer | What it tests | I/O allowed | Count |
|---|---|---|---|
| **Unit** | Single function/class in isolation | No | Most tests (~70%) |
| **Integration** | Router → service → repository → SQLite | Real SQLite (in-memory) | Some (~25%) |
| **E2E** | Full user flows via HTTP | Everything | Few (~5%) |

---

## File Structure

Mirror the source tree under `tests/`:

```
tests/
├── conftest.py                    # Shared fixtures (db session, client, factories)
├── comparers/
│   ├── test_exact_match.py
│   ├── test_pattern_match.py
│   ├── test_semantic_similarity.py
│   ├── test_llm_judge.py
│   └── test_json_schema_match.py
├── services/
│   ├── test_eval_runner.py
│   ├── test_dataset_parser.py
│   └── test_vector_store_service.py
├── db/
│   └── test_repositories.py
├── routers/
│   ├── test_configs.py
│   ├── test_datasets.py
│   ├── test_runs.py
│   └── test_vector_stores.py
└── providers/
    └── test_openai.py
```

---

## Naming Convention

```python
def test_<unit>_<scenario>[_<expected>]():
```

Examples:

```python
def test_exact_match_identical_strings_passes():
def test_exact_match_case_insensitive_ignores_case():
def test_exact_match_different_strings_fails():
def test_parse_csv_missing_input_column_raises():
def test_create_run_nonexistent_config_returns_404():
```

**Rules:**
- Start with `test_`.
- Name the unit being tested.
- Describe the scenario / input condition.
- Optionally describe the expected outcome.
- Never use generic names like `test_1`, `test_basic`, `test_it_works`.

---

## What to Test

### Always Test

| Component | What to verify |
|---|---|
| **Comparers** | Correct `score`, `passed`, `details` for various input pairs. Edge cases: empty strings, whitespace, unicode. |
| **Dataset parser** | Valid CSV parsed correctly. Missing columns rejected. Empty files rejected. Large row counts handled. |
| **Repositories** | CRUD operations return correct data. Filters work. Not-found returns `None`. |
| **Services** | Business logic correctness. Error propagation. Concurrency behavior (semaphore respected). |
| **Route handlers** | Status codes (200, 303, 404, 422). Correct template rendered. Redirect targets. |

### Don't Test

| Skip | Why |
|---|---|
| SQLAlchemy model field definitions | The migration tests this implicitly |
| Pydantic Settings loading | Pydantic already tests this |
| Third-party library internals | Not our code |
| Private helper functions directly | Test them through the public function that calls them |
| Jinja2 template rendering details | Integration tests cover this via HTTP responses |

---

## Fixtures

### Shared Fixtures (`conftest.py`)

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from httpx import AsyncClient, ASGITransport

from ai_eval.app import create_app
from ai_eval.db.session import Base


@pytest.fixture
async def db_session():
    """In-memory SQLite session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSession(engine) as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def client(db_session):
    """Test HTTP client with overridden DB dependency."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

### Factory Fixtures

Use factories to create test data with sensible defaults:

```python
@pytest.fixture
def make_eval_config():
    """Factory for creating EvalConfig instances with defaults."""
    def _make(**overrides) -> EvalConfig:
        defaults = {
            "name": "Test Config",
            "system_prompt": "You are a helpful assistant.",
            "model": "gpt-4.1",
            "temperature": 0.0,
            "comparer_type": "exact_match",
            "comparer_config": {},
            "concurrency": 5,
        }
        defaults.update(overrides)
        return EvalConfig(**defaults)
    return _make
```

### Rules

- **Every fixture has a docstring.**
- **Fixtures are in `conftest.py`** at the appropriate directory level — shared fixtures at `tests/conftest.py`, module-specific fixtures in their own `conftest.py`.
- **No `setUp`/`tearDown`** methods — use pytest fixtures exclusively.
- **Async fixtures** use `@pytest.fixture` (pytest-asyncio auto mode).

---

## Mocking Rules

### What to Mock

| Mock this | Why |
|---|---|
| **OpenAI API calls** | Expensive, rate-limited, non-deterministic |
| **File system** (for upload tests) | Tests should be hermetic |
| **External HTTP calls** | Network-dependent |
| **Time/datetime** (when testing timestamps) | Reproducibility |

### What NOT to Mock

| Don't mock | Why |
|---|---|
| **SQLite (in tests)** | Use in-memory SQLite — it's fast and tests real SQL |
| **The thing you're testing** | Defeats the purpose |
| **Dataclasses / Pydantic models** | Use real instances |
| **Internal functions** of the module under test | Test behavior, not implementation |

### How to Mock

Use `unittest.mock.AsyncMock` for async functions, patch at the call site:

```python
from unittest.mock import AsyncMock, patch


async def test_eval_runner_calls_openai(make_eval_config):
    mock_client = AsyncMock()
    mock_client.create_response.return_value = OpenAIResponse(
        text="4", prompt_tokens=10, completion_tokens=5
    )

    runner = EvalRunner(openai_client=mock_client, config_repo=mock_repo)
    result = await runner.evaluate_row(row={"input": "2+2", "expected_output": "4"}, config=make_eval_config())

    assert result.actual_output == "4"
    mock_client.create_response.assert_called_once()
```

**Rules:**
- Prefer **dependency injection** over `@patch`. If you can pass a mock as a constructor arg, do that.
- Use `@patch` only for module-level functions or things you can't inject.
- **Patch at the import site**, not the definition site: `@patch("ai_eval.services.eval_runner.openai_client")` not `@patch("ai_eval.services.openai_client")`.

---

## Assertion Style

- **One logical assertion per test.** Closely related assertions (e.g. `score` + `passed` on the same result) are fine together.
- Use plain `assert`, not `self.assertEqual`.
- Use `pytest.raises` for expected exceptions.
- Use `pytest.approx` for floating-point comparisons.

```python
async def test_semantic_similarity_above_threshold():
    result = comparer.compare("hello world", "hi world", {"threshold": 0.7})
    assert result.passed is True
    assert result.score == pytest.approx(0.85, abs=0.1)


async def test_parse_csv_missing_column_raises():
    with pytest.raises(DatasetValidationError, match="Missing required column: input"):
        parse_csv(bad_csv_content)
```

---

## Test Execution

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=ai_eval --cov-report=term-missing

# Run a specific test file
uv run pytest tests/comparers/test_exact_match.py

# Run tests matching a keyword
uv run pytest -k "llm_judge"

# Run with verbose output
uv run pytest -v
```

### CI Requirements

- All tests must pass before merge.
- Coverage target: **80%** minimum (enforced in CI, not a hard gate initially).
- Tests must complete in under **60 seconds** (excluding E2E).

---

## Edge Cases to Always Cover

| Category | Edge cases |
|---|---|
| **Strings** | Empty string, whitespace-only, unicode, very long strings, newlines |
| **Numbers** | Zero, negative, float precision, very large |
| **Collections** | Empty list, single item, duplicates |
| **CSV** | Empty file, header only, missing columns, extra columns, quoted fields with commas |
| **Async** | Concurrent access, cancellation, timeout |
| **IDs** | Non-existent ID, malformed UUID |

---

## Do's and Don'ts

### Do

- Write tests before or alongside the code (not weeks later).
- Use factories for test data — avoid duplicating setup.
- Test edge cases and error paths, not just the happy path.
- Keep tests independent — no test should depend on another test's state.
- Run tests locally before pushing.

### Don't

- Don't test implementation details — test behavior.
- Don't use `time.sleep()` in tests — mock time or use async patterns.
- Don't create shared mutable state between tests.
- Don't ignore flaky tests — fix or remove them.
- Don't test that Python works (e.g. testing that `dict.get` returns `None` for missing keys).
