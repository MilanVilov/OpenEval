# Skill: API & Routing — FastAPI JSON API + React Router

This skill defines how all FastAPI API endpoints and React Router routes are structured in OpenEval. The backend is a pure JSON API; the frontend is a React SPA. Follow these rules for every route handler and frontend route.

---

## URL Conventions

### Backend API Routes

All backend routes are prefixed with `/api/`. Use plural nouns. RESTful structure:

| Pattern | Method | Purpose |
|---|---|---|
| `/api/{resources}` | GET | List (returns JSON array) |
| `/api/{resources}` | POST | Create (accepts JSON body, returns created object) |
| `/api/{resources}/{id}` | GET | Detail (returns JSON object) |
| `/api/{resources}/{id}` | PUT | Update (accepts JSON body, returns updated object) |
| `/api/{resources}/{id}` | DELETE | Delete (returns 204) |
| `/api/{resources}/{id}/{sub}` | GET | Sub-resource (e.g. progress, results) |

### Frontend Routes (React Router)

Client-side routes have no prefix. React Router handles all navigation.

```
/                    → Dashboard
/configs             → Config list
/configs/new         → Create config form
/configs/:id         → Config detail
/configs/:id/edit    → Edit config
/datasets            → Dataset list
/datasets/:id        → Dataset detail
/runs                → Run list
/runs/new            → New run form
/runs/:id            → Run detail
/runs/compare        → Run comparison
/vector-stores       → Vector store list
/vector-stores/:id   → Vector store detail
```

### Concrete API Routes

```
GET    /api/configs              → List eval configs
POST   /api/configs              → Create config
GET    /api/configs/{id}         → Config detail
PUT    /api/configs/{id}         → Update config
DELETE /api/configs/{id}         → Delete config

GET    /api/datasets             → List datasets
POST   /api/datasets             → Upload CSV (multipart form)
GET    /api/datasets/{id}        → Dataset detail + preview rows
DELETE /api/datasets/{id}        → Delete dataset

GET    /api/vector-stores        → List vector stores
POST   /api/vector-stores        → Create vector store
GET    /api/vector-stores/{id}   → Store detail
POST   /api/vector-stores/{id}/files → Upload file
DELETE /api/vector-stores/{id}   → Delete store

GET    /api/runs                 → List runs
POST   /api/runs                 → Start run
GET    /api/runs/{id}            → Run detail
GET    /api/runs/{id}/progress   → Progress (for polling)
GET    /api/runs/{id}/results    → Results (with filter query params)
GET    /api/runs/compare         → Comparison data for two runs

GET    /api/dashboard            → Dashboard summary data
```

---

## Router Structure

Each router lives in its own file under `src/routers/`. One router per resource.

```python
# src/routers/configs.py
from fastapi import APIRouter, Depends
from src.db.repositories import ConfigRepository
from src.routers.schemas.configs import ConfigResponse, CreateConfigRequest

router = APIRouter(prefix="/api/configs", tags=["configs"])


@router.get("", response_model=list[ConfigResponse])
async def list_configs(repo: ConfigRepository = Depends(get_config_repo)) -> list[ConfigResponse]:
    """List all eval configurations."""
    configs = await repo.list_all()
    return [ConfigResponse.model_validate(c) for c in configs]
```

### Rules

- **One router per file**, one resource per router.
- **Router prefix** includes `/api/`: `prefix="/api/configs"`.
- **Tags** match the resource for OpenAPI docs.
- **All handlers are `async def`.**
- **Handlers return Pydantic models** — JSONResponse is implicit. Never return HTML.
- **Handlers are thin** — max 10 lines of logic. Delegate to services/repositories.
- **No business logic in handlers** — only: parse request → call service → return response.

---

## Request/Response Schemas

Pydantic models for all request bodies and responses. Schemas live in `src/routers/schemas/`, one file per resource.

```python
# src/routers/schemas/configs.py
from pydantic import BaseModel


class CreateConfigRequest(BaseModel):
    name: str
    system_prompt: str
    model: str
    temperature: float = 0.0
    comparer_type: str
    comparer_config: dict = {}
    concurrency: int = 5


class ConfigResponse(BaseModel):
    id: str
    name: str
    system_prompt: str
    model: str
    temperature: float
    comparer_type: str
    created_at: str

    model_config = {"from_attributes": True}
```

### Rules

- Separate Create/Update request models from Response models.
- Use `model_config = {"from_attributes": True}` for ORM model conversion.
- Use `response_model=` on the route decorator for automatic serialization and OpenAPI docs.
- Never return raw dicts — always use a Pydantic response model.

---

## Error Handling

All error responses are JSON. Never return HTML.

### Not Found

Use `HTTPException` with a detail string (serialized as JSON automatically):

```python
from fastapi import HTTPException

config = await repo.get_by_id(config_id)
if not config:
    raise HTTPException(status_code=404, detail="Configuration not found")
```

### Validation Errors

FastAPI handles Pydantic validation automatically — invalid request bodies return 422 with Pydantic error details.

### Server Errors

Global exception handler returns JSON:

```python
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def server_error(request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
```

---

## Polling Pattern

Progress endpoints return JSON with status, progress count, and total. The React frontend polls this every 2s via `setInterval`.

```python
@router.get("/{run_id}/progress", response_model=RunProgressResponse)
async def run_progress(run_id: str, repo=Depends(get_run_repo)):
    """Return current progress for an eval run."""
    run = await repo.get_by_id(run_id)
    return RunProgressResponse(status=run.status, progress=run.progress, total=run.total_rows)
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
- No template dependencies — there are no templates.

---

## CORS Configuration

Required for local development where the React dev server (`localhost:5173`) makes requests to the FastAPI backend (`localhost:8000`).

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # ["http://localhost:5173"] in dev
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Static File Serving (Production)

In production, serve the built React app as a static SPA. This must be mounted **after** all API routes.

```python
from fastapi.staticfiles import StaticFiles

# In production, serve the built React app
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="spa")
```

---

## Do's and Don'ts

### Do

- Return JSON from all API endpoints.
- Use Pydantic schemas for all request bodies and responses.
- Prefix all backend routes with `/api/`.
- Keep handlers under 10 lines of logic.
- Use `Depends()` for all handler dependencies.
- Use `response_model=` on route decorators.
- Validate input via Pydantic models — let FastAPI handle 422s.

### Don't

- Don't return HTML from any endpoint.
- Don't use `TemplateResponse` or `HTMLResponse`.
- Don't use `Form()` parameters — use Pydantic `Body` / request models instead.
- Don't use `RedirectResponse`.
- Don't mix API and SPA serving logic.
- Don't put SQL queries in route handlers.
- Don't use path parameters for filtering — use query parameters (`?status=failed`).
- Don't create nested routers (`/configs/{id}/runs/{run_id}`) — keep URLs shallow.
