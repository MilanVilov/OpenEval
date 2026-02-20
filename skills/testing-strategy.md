# Skill: Testing Strategy — What, How, and When to Test

**Tests are written in the same PR as the feature. A feature without tests is not done.**

This skill defines testing conventions for OpenEval. Backend tests use pytest; frontend E2E tests use Playwright.

---

## Test Pyramid

```
         ╱  E2E — Playwright (few)  ╲     Full user flows in browser
        ╱  Integration — pytest      ╲    API → service → repo → SQLite
       ╱   Unit — pytest (most)       ╲   Pure logic, no I/O
```

| Layer | Tool | What it tests | I/O | Count |
|---|---|---|---|---|
| **Unit** | pytest | Comparers, parsers, pure functions | No | ~60% |
| **Integration** | pytest + httpx | API endpoints → DB round-trips | In-memory SQLite | ~25% |
| **E2E** | Playwright | Full user flows via browser | Everything | ~15% |

---

## File Structure

```
tests/                          # Backend tests (pytest)
├── conftest.py
├── comparers/
│   ├── test_exact_match.py
│   └── ...
├── services/
├── db/
├── routers/                    # API endpoint tests
│   ├── test_configs_api.py
│   └── ...
└── providers/

frontend/e2e/                   # Frontend tests (Playwright)
├── configs.spec.ts
├── datasets.spec.ts
├── runs.spec.ts
├── vector-stores.spec.ts
└── fixtures/                   # Test helpers, page objects
```

---

## Backend Test Naming

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
| **Route handlers** | Status codes (200, 201, 204, 404, 422). **JSON response body shape matches Pydantic schema.** Correct data returned. No HTML assertions. |

### Don't Test

| Skip | Why |
|---|---|
| SQLAlchemy model field definitions | The migration tests this implicitly |
| Pydantic Settings loading | Pydantic already tests this |
| Third-party library internals | Not our code |
| Private helper functions directly | Test them through the public function that calls them |
| React component rendering details | E2E tests cover user-visible behavior |

---

## Backend Fixtures

### Shared Fixtures (`conftest.py`)

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from httpx import AsyncClient, ASGITransport

from open_eval.app import create_app
from open_eval.db.session import Base, get_session


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
    """Test HTTP client for JSON API testing."""
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

### Test Examples — JSON API

```python
async def test_list_configs_empty(client):
    response = await client.get("/api/configs")
    assert response.status_code == 200
    assert response.json() == []

async def test_create_config(client):
    response = await client.post("/api/configs", json={
        "name": "Test", "system_prompt": "...", "model": "gpt-4.1",
        "comparer_type": "exact_match"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test"
    assert "id" in data
```

### Rules

- **Every fixture has a docstring.**
- **Fixtures are in `conftest.py`** at the appropriate directory level — shared fixtures at `tests/conftest.py`, module-specific fixtures in their own `conftest.py`.
- **No `setUp`/`tearDown`** methods — use pytest fixtures exclusively.
- **Async fixtures** use `@pytest.fixture` (pytest-asyncio auto mode).

---

## Playwright E2E Tests

### Configuration

- Directory: `frontend/e2e/`
- Config: `frontend/playwright.config.ts`
- Naming: `<resource>.spec.ts`

### Pattern

```ts
import { test, expect } from '@playwright/test';

test('create eval config', async ({ page }) => {
  await page.goto('/configs/new');
  await page.fill('[name="name"]', 'Test Config');
  await page.fill('[name="system_prompt"]', 'You are helpful.');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/configs\/.+/);
  await expect(page.locator('h1')).toContainText('Test Config');
});
```

### Guidelines

- Mock API when testing frontend in isolation: `page.route('/api/**', ...)`
- Test against real backend for true E2E.
- Use page objects in `frontend/e2e/fixtures/` for shared interactions.
- Keep tests independent — each test starts from a clean state.

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
- **Patch at the import site**, not the definition site: `@patch("open_eval.services.eval_runner.openai_client")` not `@patch("open_eval.services.openai_client")`.

---

## Assertion Style

- **One logical assertion per test.** Closely related assertions (e.g. `score` + `passed` on the same result) are fine together.
- Use plain `assert`, not `self.assertEqual`.
- Use `pytest.raises` for expected exceptions.
- Use `pytest.approx` for floating-point comparisons.
- For Playwright: use `expect()` matchers.

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

## Test Execution

```bash
# Backend
uv run pytest
uv run pytest --cov=open_eval --cov-report=term-missing

# Run a specific test file
uv run pytest tests/comparers/test_exact_match.py

# Run tests matching a keyword
uv run pytest -k "llm_judge"

# Run with verbose output
uv run pytest -v

# Frontend E2E
cd frontend && npx playwright test
npx playwright test --ui  # interactive mode
```

### CI Requirements

- All tests (backend + Playwright) must pass before merge.
- Coverage target: **80%** minimum (enforced in CI, not a hard gate initially).
- Backend tests must complete in under **60 seconds** (excluding E2E).

---

## Do's and Don'ts

### Do

- Write tests with every feature — in the same PR.
- Test JSON response shapes against expected structure.
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
- Don't skip tests for "simple" features — they still need coverage.
