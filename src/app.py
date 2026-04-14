"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Handle startup and shutdown lifecycle events."""
    settings = get_settings()
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
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
        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str) -> FileResponse:
            """Serve the SPA index.html for all non-API routes."""
            file_path = spa_dir / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(spa_dir / "index.html")

    return app
