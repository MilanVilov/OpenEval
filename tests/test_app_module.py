"""Tests for deployment compatibility imports."""

from fastapi import FastAPI

from app import app, create_app


def test_root_app_module_exposes_fastapi_app() -> None:
    """The root app module should expose a FastAPI instance for Uvicorn."""
    assert isinstance(app, FastAPI)


def test_root_app_module_reexports_app_factory() -> None:
    """The root app module should re-export the application factory."""
    created_app = create_app()
    assert isinstance(created_app, FastAPI)

