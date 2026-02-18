"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ai_eval.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


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
    app = FastAPI(title="ai-eval", lifespan=lifespan)

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
        from ai_eval.routers import router

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
    for candidate in candidates:
        if candidate.is_dir():
            app.mount("/", StaticFiles(directory=str(candidate), html=True), name="spa")
            break

    return app
