# Skill: KISS & YAGNI — Simplicity-First Development

This skill enforces the KISS (Keep It Simple, Stupid) and YAGNI (You Aren't Gonna Need It) principles across all ai-eval code. These apply to Python, templates, CSS, architecture decisions, and configuration.

---

## KISS — Keep It Simple, Stupid

The simplest solution that works is the correct solution.

### Rules

1. **Flat over nested.** If code indents more than 2 levels, refactor.

```python
# BAD: nested logic
async def get_run_summary(run_id: str) -> dict:
    run = await repo.get_by_id(run_id)
    if run:
        if run.status == "completed":
            results = await repo.get_results(run_id)
            if results:
                passed = [r for r in results if r.passed]
                return {"accuracy": len(passed) / len(results)}
    return {}

# GOOD: flat with early returns
async def get_run_summary(run_id: str) -> RunSummary:
    run = await repo.get_by_id(run_id)
    if not run or run.status != "completed":
        raise NotFoundError(f"No completed run with id {run_id}")

    results = await repo.get_results(run_id)
    passed = sum(1 for r in results if r.passed)
    return RunSummary(accuracy=passed / len(results))
```

2. **Standard library first.** Don't add a dependency for something Python already does.

```python
# BAD: pip install python-dateutil just for this
from dateutil.parser import parse
created = parse("2026-01-15T10:30:00Z")

# GOOD: stdlib handles ISO format fine
from datetime import datetime
created = datetime.fromisoformat("2026-01-15T10:30:00Z")
```

3. **No abstractions without two uses.** Don't create a base class, protocol, or factory until you have at least two concrete implementations.

4. **Straightforward data flow.** Data should flow in one direction: router → service → repository → database. No callbacks, no event buses, no observer patterns unless there's a proven need.

5. **Avoid metaprogramming.** No metaclasses, no `__init_subclass__` hacks, no dynamic class generation. The comparer registry pattern (`@register_comparer` decorator) is the maximum acceptable metaprogramming.

6. **Plain functions over classes** when there's no state to manage.

```python
# BAD: stateless class used as a namespace
class CsvValidator:
    @staticmethod
    def validate_columns(columns: list[str]) -> None:
        ...
    @staticmethod
    def validate_row_count(count: int) -> None:
        ...

# GOOD: plain module functions
def validate_columns(columns: list[str]) -> None:
    ...

def validate_row_count(count: int) -> None:
    ...
```

7. **One way to do things.** If there are two patterns for the same task in the codebase, delete one. Consistency beats local optimization.

---

## YAGNI — You Aren't Gonna Need It

Don't build it until you need it. Speculative code is a maintenance burden.

### Rules

1. **No premature abstraction.** Only abstract when you have a concrete second use case.

```python
# BAD: building a plugin system for dataset parsers when we only support CSV
class BaseDatasetParser(ABC):
    @abstractmethod
    def parse(self, file: BinaryIO) -> list[dict]: ...

class CsvParser(BaseDatasetParser):
    def parse(self, file: BinaryIO) -> list[dict]: ...

class JsonlParser(BaseDatasetParser):  # nobody asked for this
    def parse(self, file: BinaryIO) -> list[dict]: ...

# GOOD: just a function until there's a real second format
def parse_csv(file: BinaryIO) -> list[dict]:
    """Parse uploaded CSV into list of row dicts."""
    ...
```

2. **No unused parameters.** Don't add function parameters "for the future." Add them when they're needed.

```python
# BAD
async def create_run(config_id: str, dataset_id: str, *, 
                     tags: list[str] | None = None,       # not used anywhere yet
                     priority: int = 0,                     # not used anywhere yet
                     webhook_url: str | None = None,        # not used anywhere yet
                     ) -> EvalRun:

# GOOD
async def create_run(config_id: str, dataset_id: str) -> EvalRun:
```

3. **No speculative configuration.** Don't make something configurable until a user actually needs to change it. Start with a sensible hardcoded default.

```python
# BAD: making everything configurable from day 1
HTMX_POLL_INTERVAL = int(os.getenv("HTMX_POLL_INTERVAL", "2000"))
MAX_CSV_PREVIEW_ROWS = int(os.getenv("MAX_CSV_PREVIEW_ROWS", "10"))
TABLE_PAGE_SIZE = int(os.getenv("TABLE_PAGE_SIZE", "50"))

# GOOD: hardcode it, extract to config only when someone needs flexibility
POLL_INTERVAL_MS = 2000
PREVIEW_ROWS = 10
PAGE_SIZE = 50
```

4. **No feature flags without features.** Don't build toggle infrastructure before you have something to toggle.

5. **No dead code.** If code is commented out or behind `if False:`, delete it. Version control remembers.

6. **No "just in case" error handling.**

```python
# BAD: handling errors that can't happen
try:
    score = passed_count / total_count
except ZeroDivisionError:
    score = 0.0  # "just in case"
except TypeError:
    score = 0.0  # "just in case"
except ValueError:
    score = 0.0  # "just in case"

# GOOD: handle only what can actually happen
if total_count == 0:
    score = 0.0
else:
    score = passed_count / total_count
```

---

## Architecture YAGNI — What NOT to Build

These are common over-engineering traps. Do NOT build until there's a proven need:

| Don't build | Instead |
|---|---|
| Event system / message bus | Direct function calls |
| Caching layer | SQLite is fast enough for local use |
| Rate limiter middleware | `asyncio.Semaphore` in the eval runner is sufficient |
| Background job queue (Celery, etc.) | FastAPI `BackgroundTasks` |
| User/role system | No auth — it's a shared local tool |
| API versioning (`/v1/`, `/v2/`) | Single version, change in place |
| WebSocket for progress | HTMX polling every 2s is fine |
| Pagination framework | Simple limit/offset in SQL |
| Custom ORM query builder | SQLAlchemy is the query builder |
| Configuration file format (YAML/TOML) | Environment variables via Pydantic Settings |

---

## Checklist Before Writing Code

Ask yourself:

1. **Does this solve a problem we have today?** If no, don't write it.
2. **Is this the simplest way to solve it?** If you can think of a simpler way, use that.
3. **Can I delete this later without breaking anything?** If removing it would be painful, the coupling is too tight.
4. **Would a new contributor understand this in under a minute?** If not, simplify.

---

## Do's and Don'ts

### Do

- Write the dumbest code that works, then stop.
- Delete code that isn't earning its keep.
- Use built-in Python features before reaching for a library.
- Hardcode first, configure later (only when needed).
- Refactor to simplify, not to add flexibility.

### Don't

- Don't build "framework-like" infrastructure for a single use case.
- Don't add configuration options nobody has asked for.
- Don't create abstractions for abstractions' sake.
- Don't keep dead code, unused imports, or commented-out blocks.
- Don't optimize performance before measuring a problem.
- Don't design for scale you don't have — this app runs on one machine.
