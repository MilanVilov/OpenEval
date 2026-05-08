"""FastAPI application factory."""

import json
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import FastAPI, HTTPException, Request
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
    file_path = _safe_spa_file(spa_dir, request_path)
    if file_path is not None:
        return file_path
    if not base_path or not request_path.startswith(f"{base_path}/"):
        return None
    prefixed_path = request_path.removeprefix(base_path).lstrip("/")
    return _safe_spa_file(spa_dir, prefixed_path)


def _safe_spa_file(spa_dir: Path, relative_path: str) -> Path | None:
    """Return a built SPA file only when it remains inside ``spa_dir``."""
    spa_root = spa_dir.resolve()
    candidate = (spa_root / unquote(relative_path).lstrip("/")).resolve()
    try:
        candidate.relative_to(spa_root)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    return None


def _is_spa_asset_path(request_path: str, base_path: str) -> bool:
    """Return whether the request targets a built SPA asset."""
    path = unquote(request_path)
    return path.startswith("/assets/") or (
        bool(base_path) and path.startswith(f"{base_path}/assets/")
    )


def _prefix_root_relative_urls(index_html: str, base_path: str) -> str:
    """Prefix entrypoint asset URLs in the SPA entrypoint for subpath deploys."""
    if not base_path:
        return index_html

    def prefix_match(match: re.Match[str]) -> str:
        attr = match.group("attr")
        path = match.group("path")
        if path == base_path or path.startswith(f"{base_path}/"):
            return match.group(0)
        normalized_path = "/" + path.removeprefix("./").lstrip("/")
        return f"{attr}{base_path}{normalized_path}"

    return re.sub(
        r'(?P<attr>\b(?:href|src)=["\'])(?P<path>(?:/(?!/)|\./)[^"\']*)',
        prefix_match,
        index_html,
    )


def _inject_spa_base_path(index_html: str, base_path: str) -> str:
    """Inject the runtime base path used by the React router."""
    base_tag = f'<base href="{base_path}/">\n' if base_path else ""
    config_script = f"{base_tag}<script>window.APP_BASE_URL = {json.dumps(base_path)};</script>"
    module_script = '<script type="module"'
    if module_script in index_html:
        return index_html.replace(module_script, f"{config_script}\n{module_script}", 1)
    if "</head>" in index_html:
        return index_html.replace("</head>", f"{config_script}\n</head>", 1)
    return f"{config_script}\n{index_html}"


def _get_request_base_path(request: Request, configured_base_path: str) -> str:
    """Return the effective SPA base path for the current request."""
    if configured_base_path:
        return configured_base_path
    root_path = request.scope.get("root_path", "")
    if root_path:
        return _normalize_base_path(root_path)
    forwarded_prefix = request.headers.get("x-forwarded-prefix", "")
    return _normalize_base_path(forwarded_prefix)


def _mount_spa_assets(app: FastAPI, spa_dir: Path, base_path: str) -> None:
    """Mount built SPA assets at root and at the configured base path."""
    assets_dir = str(spa_dir / "assets")
    if base_path:
        app.mount(
            f"{base_path}/assets",
            StaticFiles(directory=assets_dir),
            name="prefixed-static-assets",
        )
    app.mount("/assets", StaticFiles(directory=assets_dir), name="static-assets")


def _include_api_routers(app: FastAPI, base_path: str) -> None:
    """Include API routers at root and under the configured SPA base path."""
    try:
        from src.routers import router
    except (ImportError, AttributeError):
        return

    app.include_router(router)
    if base_path:
        app.include_router(router, prefix=base_path)


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
    _include_api_routers(app, spa_base_path)

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
        _mount_spa_assets(app, spa_dir, spa_base_path)

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
            if _is_spa_asset_path(request_path, effective_base_path):
                raise HTTPException(status_code=404, detail="Asset not found")

            index_html = (spa_dir / "index.html").read_text(encoding="utf-8")
            index_html = _inject_spa_base_path(index_html, effective_base_path)
            return HTMLResponse(_prefix_root_relative_urls(index_html, effective_base_path))

    return app
