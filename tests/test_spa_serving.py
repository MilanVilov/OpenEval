"""Tests for SPA static asset serving."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.app as app_module
from src.app import create_app
from src.config import get_settings


def test_spa_index_prefixes_assets_for_base_url(
    monkeypatch: pytest.MonkeyPatch, spa_build: Path
) -> None:
    """The SPA entrypoint should prefix asset URLs when served from a subpath."""
    monkeypatch.setenv("APP_BASE_URL", "https://example.test/evals")
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/evals")

    assert response.status_code == 200
    assert 'window.APP_BASE_URL = "/evals";' in response.text
    assert 'src="/evals/assets/' in response.text
    assert 'href="/evals/assets/' in response.text
    assert 'href="/evals/vite.svg"' in response.text

    get_settings.cache_clear()


def test_spa_serves_assets_under_base_url(
    monkeypatch: pytest.MonkeyPatch, spa_build: Path
) -> None:
    """Built frontend files should be reachable under the configured base URL."""
    monkeypatch.setenv("APP_BASE_URL", "/evals")
    get_settings.cache_clear()

    app = create_app()
    asset_path = _first_asset_path(spa_build)
    with TestClient(app) as client:
        response = client.get(f"/evals/{asset_path}")

    assert response.status_code == 200
    assert response.text == "body{margin:0}"

    get_settings.cache_clear()


def test_spa_prefixes_assets_from_forwarded_prefix(
    monkeypatch: pytest.MonkeyPatch, spa_build: Path
) -> None:
    """The SPA should respect a forwarded proxy prefix when no base URL is set."""
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/evals", headers={"x-forwarded-prefix": "/evals"})

    assert response.status_code == 200
    assert 'window.APP_BASE_URL = "/evals";' in response.text
    assert 'src="/evals/assets/' in response.text

    get_settings.cache_clear()


def _first_asset_path(spa_dir: Path) -> str:
    """Return the relative path for the first built asset file."""
    asset_file = sorted((spa_dir / "assets").iterdir())[0]
    return f"assets/{asset_file.name}"
