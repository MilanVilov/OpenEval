"""Tests for SPA static asset serving."""

from pathlib import Path

from fastapi.testclient import TestClient

from src.app import create_app
from src.config import get_settings


def test_spa_index_prefixes_assets_for_base_url(monkeypatch) -> None:
    """The SPA entrypoint should prefix asset URLs when served from a subpath."""
    monkeypatch.setenv("APP_BASE_URL", "https://example.test/evals")
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/evals")

    assert response.status_code == 200
    assert 'src="/evals/assets/' in response.text
    assert 'href="/evals/assets/' in response.text
    assert 'href="/evals/vite.svg"' in response.text

    get_settings.cache_clear()


def test_spa_serves_assets_under_base_url(monkeypatch) -> None:
    """Built frontend files should be reachable under the configured base URL."""
    monkeypatch.setenv("APP_BASE_URL", "/evals")
    get_settings.cache_clear()

    app = create_app()
    asset_path = _first_asset_path()
    with TestClient(app) as client:
        response = client.get(f"/evals/{asset_path}")

    assert response.status_code == 200
    assert response.text

    get_settings.cache_clear()


def test_spa_prefixes_assets_from_forwarded_prefix(monkeypatch) -> None:
    """The SPA should respect a forwarded proxy prefix when no base URL is set."""
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/evals", headers={"x-forwarded-prefix": "/evals"})

    assert response.status_code == 200
    assert 'src="/evals/assets/' in response.text

    get_settings.cache_clear()


def _first_asset_path() -> str:
    """Return the relative path for the first built asset file."""
    spa_assets_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist" / "assets"
    asset_file = next(spa_assets_dir.iterdir())
    return f"assets/{asset_file.name}"
