# Skill: KISS & YAGNI — Simplicity-First Development

This skill enforces the KISS (Keep It Simple, Stupid) and YAGNI (You Aren't Gonna Need It) principles across all OpenEval code. These apply to Python, React components, CSS, architecture decisions, and configuration.

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

## Frontend KISS Rules

1. **Plain `fetch` over data-fetching libraries.** For this app's size, `fetch` + `useState`/`useEffect` is sufficient. No React Query, no SWR, no Axios.

```tsx
// BAD: adding a data-fetching library for a simple app
import { useQuery } from '@tanstack/react-query';
const { data } = useQuery(['configs'], fetchConfigs);

// GOOD: plain fetch
const [configs, setConfigs] = useState<Config[]>([]);
useEffect(() => {
  fetch('/api/configs').then(r => r.json()).then(setConfigs);
}, []);
```

2. **`useState`/`useEffect` over state management libraries.** No Redux, no Zustand, no Jotai. Component-local state and prop drilling are fine for this app.

3. **One component per file, under 100 lines.** If a component exceeds 100 lines, split it.

4. **Tailwind classes over custom CSS files.** Use Tailwind utility classes directly. No custom CSS unless Tailwind genuinely can't express it.

5. **Shadcn/ui components over custom implementations.** Don't build buttons, dialogs, tables, or form controls from scratch — use Shadcn/ui.

```tsx
// BAD: custom modal implementation
function Modal({ open, children }) {
  if (!open) return null;
  return <div className="fixed inset-0 bg-black/50">...</div>;
}

// GOOD: use Shadcn/ui
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
```

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
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2000"))
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
| WebSocket for progress | `setInterval` + fetch polling is fine |
| Redux / Zustand / Jotai | `useState` + `useEffect` is sufficient |
| React Query / SWR | Plain fetch is fine for this app size |
| CSS-in-JS (styled-components) | Tailwind CSS |
| Server-side rendering (Next.js) | Vite SPA is sufficient |
| Custom component library | Shadcn/ui covers all needs |
| Event system / message bus | Direct function calls |
| Caching layer | SQLite is fast enough |
| Background job queue (Celery) | FastAPI BackgroundTasks |
| User/role system | No auth |
| API versioning | Single version |
| Pagination framework | Simple limit/offset |
| Custom ORM query builder | SQLAlchemy is the query builder |
| Config file format (YAML) | Environment variables via Pydantic Settings |

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
- Use Shadcn/ui components before building custom ones.
- Hardcode first, configure later (only when needed).
- Refactor to simplify, not to add flexibility.

### Don't

- Don't build "framework-like" infrastructure for a single use case.
- Don't add configuration options nobody has asked for.
- Don't create abstractions for abstractions' sake.
- Don't keep dead code, unused imports, or commented-out blocks.
- Don't optimize performance before measuring a problem.
- Don't design for scale you don't have — this app runs on one machine.
- Don't install a library when plain `fetch` or `useState` will do.
