# Skill: Python Code Quality — SOLID, Readable, Simple

This skill defines the Python coding standards for ai-eval. All Python code MUST follow these rules. Readability and simplicity are non-negotiable.

---

## Core Principles

1. **Readable first** — code is read 10x more than it's written. Optimize for the reader.
2. **Simple over clever** — if a junior developer can't understand it in 30 seconds, simplify it.
3. **Small units** — short functions, small classes, thin modules.
4. **Explicit over implicit** — no magic. Name things clearly. Make data flow obvious.
5. **SOLID** — follow all five principles (detailed below).

---

## SOLID Principles

### S — Single Responsibility

Every class and function does **one thing**.

```python
# BAD: function does parsing AND validation AND saving
def process_dataset(file) -> Dataset:
    rows = csv.reader(file)
    if "input" not in rows[0]:
        raise ValueError("Missing input column")
    db.save(Dataset(rows=rows))

# GOOD: each concern is separate
def parse_csv(file) -> list[dict]:
    """Parse CSV file into list of row dicts."""
    ...

def validate_columns(columns: list[str]) -> None:
    """Raise ValueError if required columns are missing."""
    ...

async def save_dataset(dataset: Dataset) -> Dataset:
    """Persist dataset to database."""
    ...
```

**Rules:**
- Functions do one thing. If you use "and" to describe it, split it.
- Classes represent one concept. If the class has methods that don't use the same set of attributes, split it.
- Routers only handle HTTP — no business logic, no direct DB queries. Routers parse the JSON request body, call a service, return a Pydantic response model.
- Services contain business logic — no HTTP concerns, no SQL.
- Repositories handle data access — no business logic.

### O — Open/Closed

Open for extension, closed for modification.

```python
# GOOD: new comparers extend BaseComparer without modifying existing code
class BaseComparer(ABC):
    @abstractmethod
    def compare(self, expected: str, actual: str, config: dict) -> CompareResult:
        ...

@register_comparer("exact_match")
class ExactMatchComparer(BaseComparer):
    def compare(self, expected: str, actual: str, config: dict) -> CompareResult:
        ...
```

**Rules:**
- Use abstract base classes for extension points (comparers, providers, parsers).
- Use the registry/decorator pattern to add new implementations.
- Never modify a base class to accommodate a specific implementation.
- Configuration goes in data (JSON, env vars), not in conditionals.

### L — Liskov Substitution

Subtypes must be substitutable for their base types without breaking behavior.

```python
# BAD: subclass changes the contract
class BaseComparer(ABC):
    @abstractmethod
    def compare(self, expected: str, actual: str, config: dict) -> CompareResult:
        ...

class BrokenComparer(BaseComparer):
    def compare(self, expected: str, actual: str, config: dict) -> str:  # wrong return type!
        return "yes"

# GOOD: subclass honors the contract exactly
class ExactMatchComparer(BaseComparer):
    def compare(self, expected: str, actual: str, config: dict) -> CompareResult:
        passed = expected.strip() == actual.strip()
        return CompareResult(score=1.0 if passed else 0.0, passed=passed, details={})
```

**Rules:**
- All implementations of an ABC must accept the same parameters and return the same types.
- Never raise unexpected exceptions that the base class doesn't document.
- Type hints on every override must match the base class.

### I — Interface Segregation

Don't force classes to depend on methods they don't use.

```python
# BAD: one fat interface
class DataStore(ABC):
    @abstractmethod
    async def save_config(self, config): ...
    @abstractmethod
    async def save_dataset(self, dataset): ...
    @abstractmethod
    async def save_run(self, run): ...
    @abstractmethod
    async def query_vector_store(self, query): ...

# GOOD: focused interfaces / repository classes
class ConfigRepository:
    async def create(self, config: EvalConfig) -> EvalConfig: ...
    async def get_by_id(self, id: str) -> EvalConfig | None: ...

class DatasetRepository:
    async def create(self, dataset: Dataset) -> Dataset: ...
    async def list_all(self) -> list[Dataset]: ...
```

**Rules:**
- Keep ABCs small and focused — 1–4 methods max.
- If a class only needs part of an interface, the interface is too big.
- Prefer multiple small repository classes over one god repository.

### D — Dependency Inversion

High-level modules should not depend on low-level modules. Both depend on abstractions.

```python
# BAD: service directly imports and uses concrete DB session
from ai_eval.db.session import async_session

class EvalRunner:
    async def run(self):
        async with async_session() as db:
            ...

# GOOD: service depends on repository abstraction, injected via constructor
class EvalRunner:
    def __init__(self, config_repo: ConfigRepository, openai_client: OpenAIClient) -> None:
        self._config_repo = config_repo
        self._openai_client = openai_client

    async def run(self, config_id: str, dataset_id: str) -> EvalRun:
        config = await self._config_repo.get_by_id(config_id)
        ...
```

**Rules:**
- Services receive their dependencies via `__init__` parameters.
- Use FastAPI's `Depends()` for dependency injection in route handlers.
- Never import a concrete implementation inside a service — pass it in.
- Tests can swap in fakes/mocks because dependencies are injected.

---

## Function Rules

### Size

- **Max 20 lines** of logic (excluding docstring, blank lines, type hints).
- If a function exceeds 20 lines, extract helper functions.
- If you need a comment to explain a block, that block should be its own function with a descriptive name.

### Naming

- Functions: `verb_noun` — `parse_csv`, `validate_columns`, `create_eval_run`.
- Boolean functions: `is_` or `has_` prefix — `is_valid`, `has_required_columns`.
- Private helpers: `_` prefix — `_compute_score`.
- No abbreviations except universally understood ones (`id`, `db`, `config`, `fn`).

### Parameters

- **Max 4 parameters**. If you need more, group related params into a dataclass or TypedDict.
- No boolean flag parameters that change behavior — split into two functions instead.
- Use keyword-only arguments (`*`) for anything after the first 2 positional params.

```python
# BAD
def run_eval(config_id, dataset_id, parallel, max_retries, timeout, verbose):
    ...

# GOOD
@dataclass
class RunOptions:
    concurrency: int = 5
    max_retries: int = 3
    timeout_seconds: int = 30

async def run_eval(config_id: str, dataset_id: str, *, options: RunOptions | None = None) -> EvalRun:
    ...
```

### Return Values

- Return early for error/edge cases — avoid deep nesting.
- Never return `None` when a proper value is expected — raise an exception or use `T | None` with explicit type hint.
- Use dataclasses or NamedTuples for multi-value returns, never raw tuples.

```python
# BAD
def get_score(result):
    if result:
        if result.output:
            if result.expected:
                return result.output == result.expected
    return None

# GOOD
def get_score(result: EvalResult) -> bool:
    """Return whether the result output matches expected."""
    if not result.output or not result.expected:
        raise ValueError("Result missing output or expected value")
    return result.output.strip() == result.expected.strip()
```

---

## Class Rules

### Size

- **Max 200 lines** per file.
- **Max 10 public methods** per class.
- If a class grows beyond these limits, split responsibilities.

### Structure

Every class follows this order:

1. Class docstring
2. Class-level constants
3. `__init__`
4. Public methods
5. Private methods (`_` prefix)
6. Dunder methods (`__str__`, `__repr__`, etc.)

### Data Classes

Use `dataclass` or Pydantic `BaseModel` for data containers. Never use plain dicts for structured data that crosses function boundaries.

```python
# BAD
result = {"score": 0.95, "passed": True, "details": {"diff": "..."}}

# GOOD
@dataclass
class CompareResult:
    score: float
    passed: bool
    details: dict[str, Any]
```

---

## Pydantic Schema Conventions

Request and response schemas for API endpoints live in `src/ai_eval/routers/schemas/`, one file per resource.

- Use `model_config = {"from_attributes": True}` on response models for ORM model conversion.
- Separate Create/Update request models from Response models — do not reuse the same model for both.
- Name schemas clearly: `CreateConfigRequest`, `UpdateConfigRequest`, `ConfigResponse`.

```python
# src/ai_eval/routers/schemas/configs.py
from pydantic import BaseModel


class CreateConfigRequest(BaseModel):
    """Schema for creating a new eval configuration."""
    name: str
    system_prompt: str
    model: str
    temperature: float = 0.0
    comparer_type: str


class ConfigResponse(BaseModel):
    """Schema for returning an eval configuration."""
    id: str
    name: str
    system_prompt: str
    model: str
    temperature: float
    comparer_type: str
    created_at: str

    model_config = {"from_attributes": True}
```

---

## Error Handling

- Use **specific exceptions**, never bare `except:` or `except Exception:` (unless re-raising).
- Define custom exceptions for domain errors: `DatasetValidationError`, `ComparerError`, `OpenAIClientError`.
- Let unexpected exceptions propagate — don't swallow them.
- Always include context in error messages.
- Return JSON error responses from API endpoints — never HTML.

```python
# BAD
try:
    result = await openai_client.call(prompt)
except:
    return None

# GOOD
try:
    result = await openai_client.call(prompt)
except OpenAIClientError as e:
    raise EvalRunError(f"OpenAI call failed for row {row_index}: {e}") from e
```

---

## Type Hints

- **Every function** has full type hints — parameters and return type.
- Use `|` union syntax (Python 3.12+): `str | None`, not `Optional[str]`.
- Use `list[str]`, `dict[str, Any]`, not `List[str]`, `Dict[str, Any]`.
- Generic collections from `collections.abc`: `Sequence`, `Mapping`, `Iterable` for inputs; concrete types for outputs.
- Use `typing.TypeAlias` or `type` statement for complex types.

```python
type ComparerFactory = Callable[[dict[str, Any]], BaseComparer]
```

---

## Imports

Order (enforced by `ruff`):

1. Standard library
2. Third-party packages
3. Local/project imports

```python
import csv
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ai_eval.db.repositories import ConfigRepository
from ai_eval.routers.schemas.configs import ConfigResponse, CreateConfigRequest
from ai_eval.services.eval_runner import EvalRunner
```

**Rules:**
- No wildcard imports (`from x import *`).
- No circular imports — if two modules need each other, one of them has the wrong responsibility.
- Import modules, not deeply nested internals (import `from ai_eval.db.repositories`, not `from ai_eval.db.repositories.config_repo_impl`).

---

## Async Rules

- All I/O-bound operations are `async def`.
- Never use `time.sleep()` — use `asyncio.sleep()`.
- Never call sync I/O (file reads, HTTP requests) inside async functions without wrapping in `asyncio.to_thread()`.
- Use `asyncio.gather()` for concurrent tasks, `asyncio.Semaphore` for rate limiting.

```python
async def run_eval_rows(rows: list[dict], *, concurrency: int = 5) -> list[EvalResult]:
    """Run eval on all rows with bounded concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def process_row(row: dict) -> EvalResult:
        async with semaphore:
            return await evaluate_single_row(row)

    return await asyncio.gather(*[process_row(r) for r in rows])
```

---

## Docstrings

All public functions and classes get a docstring.

```python
async def create_eval_run(
    config_id: str,
    dataset_id: str,
    *,
    options: RunOptions | None = None,
) -> EvalRun:
    """Create and start a new evaluation run.

    Loads the config and dataset, validates compatibility,
    then spawns a background task to execute the eval.

    Args:
        config_id: UUID of the eval configuration.
        dataset_id: UUID of the dataset to evaluate against.
        options: Optional run parameters (concurrency, retries).

    Returns:
        The created EvalRun with status 'pending'.

    Raises:
        NotFoundError: If config or dataset ID doesn't exist.
        DatasetValidationError: If dataset is incompatible with config.
    """
    ...
```

**Rules:**
- First line: imperative summary ("Create…", "Return…", "Validate…").
- `Args`, `Returns`, `Raises` sections for anything non-trivial.
- Private methods: docstring optional, but add one if the logic is complex.
- One-liner docstrings for simple methods: `"""Return the comparer score."""`

---

## Complexity Rules

- **Max cyclomatic complexity: 8** per function (enforced by `ruff`).
- **No nested conditionals deeper than 2 levels** — use early returns, guard clauses, or extract functions.
- **No nested loops** — extract the inner loop into a function.
- Prefer `dict` lookups over long `if/elif` chains.

```python
# BAD
def get_status_label(status):
    if status == "pending":
        return "Pending"
    elif status == "running":
        return "Running"
    elif status == "completed":
        return "Completed"
    elif status == "failed":
        return "Failed"
    else:
        return "Unknown"

# GOOD
STATUS_LABELS: dict[str, str] = {
    "pending": "Pending",
    "running": "Running",
    "completed": "Completed",
    "failed": "Failed",
}

def get_status_label(status: str) -> str:
    """Return human-readable label for a run status."""
    return STATUS_LABELS.get(status, "Unknown")
```

---

## Testing Conventions

**Every feature must include tests. A feature without tests is not done. No PR will be accepted without accompanying tests.**

- Test file mirrors source: `src/ai_eval/services/eval_runner.py` → `tests/services/test_eval_runner.py`.
- Test function names: `test_<function>_<scenario>` — `test_parse_csv_missing_columns_raises`.
- One assertion per test (or closely related assertions).
- Use `pytest.fixture` for shared setup — no `setUp` methods.
- Mock external dependencies (OpenAI, filesystem), never mock the thing you're testing.
- Use `pytest.raises` for expected exceptions.
- Backend tests use `pytest` + `pytest-asyncio`.
- Frontend tests use Playwright for E2E testing.

```python
async def test_exact_match_comparer_case_insensitive() -> None:
    comparer = ExactMatchComparer()
    result = comparer.compare("Hello", "hello", {"case_sensitive": False})
    assert result.passed is True
    assert result.score == 1.0
```

---

## Linting & Formatting

Enforced via `ruff` in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 99

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "C90",  # mccabe complexity
    "RUF",  # ruff-specific rules
]

[tool.ruff.lint.mccabe]
max-complexity = 8
```

---

## Do's and Don'ts

### Do

- Write code that reads like prose — good names eliminate the need for comments.
- Return early to avoid nesting.
- Use dataclasses for any structured data.
- Keep every function under 20 lines of logic.
- Inject dependencies — never reach into global state from services.
- Write type hints on everything — let the type checker find bugs.
- Return Pydantic response models from all route handlers.
- Write tests for every feature — untested code is incomplete code.

### Don't

- Don't use `Any` unless absolutely unavoidable (and document why).
- Don't use global mutable state.
- Don't put business logic in route handlers — delegate to services.
- Don't catch generic exceptions.
- Don't use `# type: ignore` without a specific error code and comment.
- Don't use inheritance for code reuse — prefer composition. Inheritance is for polymorphism only (comparers, providers).
- Don't write "utils" or "helpers" modules — name the module after what it does.
- Don't return HTML from route handlers — return Pydantic models.
- Don't use `Form()`, `TemplateResponse`, `HTMLResponse`, or `RedirectResponse`.
