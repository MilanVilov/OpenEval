"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.services.scheduler import get_scheduler_service

BASE_DIR = Path(__file__).resolve().parent.parent


def _normalize_base_path(base_url: str) -> str:
    """Return a normalized URL path prefix derived from ``base_url``."""
    raw_path = urlparse(base_url).path if "://" in base_url else base_url
    path = raw_path.strip()
    if not path or path == "/":
        return ""
    return "/" + path.strip("/")


def _resolve_spa_file(spa_dir: Path, request_path: str, base_path: str) -> Path | None:
    """Return the matching built SPA file for ``request_path`` if one exists."""
    relative_path = request_path.lstrip("/")
    candidate = spa_dir / relative_path
    if candidate.is_file():
        return candidate
    if not base_path or not request_path.startswith(f"{base_path}/"):
        return None
    prefixed_path = request_path.removeprefix(base_path).lstrip("/")
    candidate = spa_dir / prefixed_path
    if candidate.is_file():
        return candidate
    return None


def _prefix_root_relative_urls(index_html: str, base_path: str) -> str:
    """Prefix root-relative asset URLs in the SPA entrypoint for subpath deploys."""
    if not base_path:
        return index_html
    return (
        index_html.replace('href="/', f'href="{base_path}/')
        .replace('src="/', f'src="{base_path}/')
    )


def _get_request_base_path(request: Request, configured_base_path: str) -> str:
    """Return the effective SPA base path for the current request."""
    if configured_base_path:
        return configured_base_path
    root_path = request.scope.get("root_path", "")
    if root_path:
        return _normalize_base_path(root_path)
    forwarded_prefix = request.headers.get("x-forwarded-prefix", "")
    return _normalize_base_path(forwarded_prefix)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Handle startup and shutdown lifecycle events."""
    settings = get_settings()
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    scheduler = get_scheduler_service()
    await scheduler.start()
    try:
        yield
    finally:
        await scheduler.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    spa_base_path = _normalize_base_path(settings.app_base_url)
    app = FastAPI(title="OpenEval", lifespan=lifespan)

    # CORS middleware for React dev server
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler — always return JSON
    @app.exception_handler(Exception)
    async def server_error(request: object, exc: Exception) -> JSONResponse:
        """Return server errors as JSON."""
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    # Include API routers
    try:
        from src.routers import router

        app.include_router(router)
    except (ImportError, AttributeError):
        pass

    # Serve React build if it exists (production Docker build)
    # Check multiple candidate paths: works both in dev (repo root) and
    # when installed as a package (e.g. inside a Docker container).
    candidates = [
        Path("/app/frontend/dist"),                   # Docker container
        BASE_DIR / "frontend" / "dist",               # running from repo root
    ]
    spa_dir: Path | None = None
    for candidate in candidates:
        if candidate.is_dir():
            spa_dir = candidate
            break

    if spa_dir is not None:
        # Serve static assets (JS, CSS, images, etc.)
        app.mount("/assets", StaticFiles(directory=str(spa_dir / "assets")), name="static-assets")

        # Catch-all: serve index.html for any non-API route so React Router
        # can handle client-side navigation on direct URL access / refresh.
        @app.get("/{full_path:path}", response_model=None)
        async def serve_spa(request: Request, full_path: str) -> FileResponse | HTMLResponse:
            """Serve the SPA index.html for all non-API routes."""
            effective_base_path = _get_request_base_path(request, spa_base_path)
            request_path = request.url.path
            file_path = _resolve_spa_file(spa_dir, request_path, effective_base_path)
            if file_path is not None:
                return FileResponse(file_path)

            index_html = (spa_dir / "index.html").read_text(encoding="utf-8")
            return HTMLResponse(_prefix_root_relative_urls(index_html, effective_base_path))

    return app
