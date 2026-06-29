"""Tests for deployment compatibility imports."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from app import app, create_app
from app.main import app as main_app
from app.main import create_app as main_create_app


def test_root_app_module_exposes_fastapi_app() -> None:
    """The root app module should expose a FastAPI instance for Uvicorn."""
    assert isinstance(app, FastAPI)


def test_root_app_module_reexports_app_factory() -> None:
    """The root app module should re-export the application factory."""
    created_app = create_app()
    assert isinstance(created_app, FastAPI)


def test_app_main_module_exposes_fastapi_app() -> None:
    """The app.main module should expose a FastAPI instance for Uvicorn."""
    assert isinstance(main_app, FastAPI)


def test_app_main_module_reexports_app_factory() -> None:
    """The app.main module should re-export the application factory."""
    created_app = main_create_app()
    assert isinstance(created_app, FastAPI)


def test_create_app_initializes_sentry() -> None:
    """The application factory should initialize Sentry from settings."""
    settings = MagicMock()
    settings.app_base_url = ""
    settings.cors_origins = ""

    with (
        patch("src.app.get_settings", return_value=settings),
        patch("src.app.init_sentry") as mock_init_sentry,
    ):
        create_app()

    mock_init_sentry.assert_called_once_with(settings)
