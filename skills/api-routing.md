# Skill: API & Routing — FastAPI + HTMX Conventions

This skill defines how all FastAPI routers, endpoints, and HTMX interactions are structured in ai-eval. Follow these rules for every route handler and template interaction.

---

## URL Conventions

### Resource URLs

Use plural nouns. RESTful structure for full-page routes, with HTMX fragment endpoints nested under the resource.

| Pattern | Method | Purpose |
|---|---|---|
| `/{resources}` | GET | List page |
| `/{resources}/new` | GET | Create form page |
| `/{resources}` | POST | Create (form submit) |
| `/{resources}/{id}` | GET | Detail page |
| `/{resources}/{id}/edit` | GET | Edit form page |
| `/{resources}/{id}` | PUT/PATCH | Update (form submit) |
| `/{resources}/{id}` | DELETE | Delete |
| `/{resources}/{id}/{fragment}` | GET | HTMX partial (e.g. progress, results table) |

### Concrete Routes

```
GET   /                          → Dashboard
GET   /configs                   → List eval configs
GET   /configs/new               → Create config form
POST  /configs                   → Create config
GET   /configs/{id}              → Config detail
GET   /configs/{id}/edit         → Edit config form
PUT   /configs/{id}              → Update config
DELETE /configs/{id}             → Delete config

GET   /datasets                  → List datasets
POST  /datasets                  → Upload CSV
GET   /datasets/{id}             → Dataset detail + preview
DELETE /datasets/{id}            → Delete dataset

GET   /vector-stores             → List vector stores
POST  /vector-stores             → Create vector store
GET   /vector-stores/{id}        → Store detail
POST  /vector-stores/{id}/files  → Upload file to store
DELETE /vector-stores/{id}       → Delete store

GET   /runs                      → List runs
GET   /runs/new                  → New run form
POST  /runs                      → Start run
GET   /runs/{id}                 → Run detail (summary + results)
GET   /runs/{id}/progress        → HTMX partial: progress bar + status
GET   /runs/{id}/results         → HTMX partial: results table (with filter params)
GET   /runs/compare              → Run comparison page
```

---

## Router Structure

Each router lives in its own file under `src/ai_eval/routers/`. One router per resource.

```python
# src/ai_eval/routers/configs.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(prefix="/configs", tags=["configs"])


@router.get("", response_class=HTMLResponse)
async def list_configs(request: Request, repo: ConfigRepository = Depends(get_config_repo)):
    """List all eval configurations."""
    configs = await repo.list_all()
    return templates.TemplateResponse("configs/list.html", {"request": request, "configs": configs})
```

### Rules

- **One router per file**, one resource per router.
- **Router prefix** matches the resource name: `prefix="/configs"`.
- **Tags** match the resource for OpenAPI docs.
- **All handlers are `async def`.**
- **Handlers are thin** — max 10 lines of logic. Delegate to services/repositories.
- **No business logic in handlers** — only: parse request → call service → return response.

---

## Request/Response Patterns

### Form Submissions (non-HTMX)

Standard HTML forms use POST, return a redirect on success:

```python
@router.post("", response_class=RedirectResponse)
async def create_config(
    request: Request,
    name: str = Form(...),
    system_prompt: str = Form(...),
    model: str = Form(...),
    repo: ConfigRepository = Depends(get_config_repo),
):
    """Create a new eval configuration."""
    config = await repo.create(EvalConfig(name=name, system_prompt=system_prompt, model=model))
    return RedirectResponse(url=f"/configs/{config.id}", status_code=303)
```

**POST-Redirect-GET pattern**: always redirect after a successful POST to prevent double-submission.

### HTMX Partials

HTMX endpoints return HTML fragments (not full pages):

```python
@router.get("/{run_id}/progress", response_class=HTMLResponse)
async def run_progress(request: Request, run_id: str, repo: RunRepository = Depends(get_run_repo)):
    """Return progress bar fragment for HTMX polling."""
    run = await repo.get_by_id(run_id)
    return templates.TemplateResponse("components/progress_bar.html", {"request": request, "run": run})
```

### Detecting HTMX Requests

Use the `HX-Request` header to decide between full page and fragment:

```python
def is_htmx(request: Request) -> bool:
    """Check if the request was made by HTMX."""
    return request.headers.get("HX-Request") == "true"
```

---

## HTMX Conventions

### Polling

For live progress (eval runs):

```html
<div hx-get="/runs/{{ run.id }}/progress"
     hx-trigger="every 2s"
     hx-swap="outerHTML">
  {% include "components/progress_bar.html" %}
</div>
```

Stop polling when complete — the fragment returned should not include `hx-trigger` when the run is finished.

### Form Submission

For inline actions (delete, toggle):

```html
<button hx-delete="/configs/{{ config.id }}"
        hx-confirm="Delete this configuration?"
        hx-target="closest tr"
        hx-swap="outerHTML swap:300ms">
  Delete
</button>
```

### Fragment Targets

- Use `hx-target` to specify where the response goes.
- Use `hx-swap="outerHTML"` for replacing elements, `"innerHTML"` for filling containers.
- Use `hx-swap="outerHTML swap:300ms"` for deletions (allows CSS fade-out).

### Loading Indicators

Use `hx-indicator` for buttons that trigger API calls:

```html
<button hx-post="/runs" class="btn-primary" hx-indicator="#spinner">
  Start Run
  <span id="spinner" class="htmx-indicator">...</span>
</button>
```

---

## Error Handling in Routes

### Validation Errors

Re-render the form with error messages — don't redirect:

```python
@router.post("", response_class=HTMLResponse)
async def create_config(request: Request, name: str = Form(...), ...):
    errors = validate_config_form(name=name, ...)
    if errors:
        return templates.TemplateResponse(
            "configs/new.html",
            {"request": request, "errors": errors, "name": name, ...},
            status_code=422,
        )
    ...
```

### Not Found

Raise `HTTPException(404)` — FastAPI will render the error page:

```python
config = await repo.get_by_id(config_id)
if not config:
    raise HTTPException(status_code=404, detail="Configuration not found")
```

### Server Errors

Let unexpected exceptions propagate. Add a global exception handler that renders a user-friendly error page:

```python
@app.exception_handler(500)
async def server_error(request: Request, exc: Exception):
    return templates.TemplateResponse("error.html", {"request": request, "error": str(exc)}, status_code=500)
```

---

## Dependency Injection

Use FastAPI `Depends()` for all handler dependencies:

```python
async def get_config_repo(session: AsyncSession = Depends(get_session)) -> ConfigRepository:
    """Provide a ConfigRepository instance."""
    return ConfigRepository(session)

async def get_openai_client(settings: Settings = Depends(get_settings)) -> OpenAIClient:
    """Provide an OpenAI client configured with the API key."""
    return OpenAIClient(api_key=settings.openai_api_key)
```

### Rules

- **Never instantiate dependencies inside handlers.** Always use `Depends()`.
- **One dependency per concern** — don't combine repo + service in one dependency.
- **Dependencies return concrete instances**, not ABCs (keep it simple).

---

## Template Rendering

Use Jinja2 `templates.TemplateResponse` for all HTML responses:

```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
```

### Context Rules

- Always pass `request` in the context (required by Starlette).
- Pass only the data the template needs — no entire database models with lazy-loaded relations.
- Use descriptive context variable names: `configs`, `run`, `results`, not `data`, `items`, `obj`.

---

## Do's and Don'ts

### Do

- Use POST-Redirect-GET for form submissions.
- Keep handlers under 10 lines of logic.
- Return HTML fragments for HTMX requests, full pages for normal requests.
- Use `Depends()` for all handler dependencies.
- Validate input in the handler, delegate business logic to services.

### Don't

- Don't put SQL queries in route handlers.
- Don't return JSON from page routes (this is an HTMX app, not a JSON API).
- Don't use path parameters for filtering — use query parameters (`?status=failed`).
- Don't create nested routers (`/configs/{id}/runs/{run_id}`) — keep URLs shallow.
- Don't mix HTMX partial endpoints with full-page endpoints in confusing ways — clearly separate them.
