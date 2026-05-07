"""Tests for async database session setup."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import src.db.session as session_mod


@pytest.fixture(autouse=True)
def _reset_engine_cache():
    """Reset cached engine state before and after each test."""
    session_mod._engine = None
    session_mod._session_factory = None
    yield
    session_mod._engine = None
    session_mod._session_factory = None


def _settings(database_url: str, *, pool_size: int = 5) -> SimpleNamespace:
    """Return a minimal settings object for session setup tests."""
    return SimpleNamespace(
        database_url=database_url,
        app_db_connection_pool=pool_size,
        resolved_database_url=lambda: database_url,
    )


def test_get_engine_skips_sqlite_pragma_for_mysql(monkeypatch: pytest.MonkeyPatch) -> None:
    """MySQL engines should not receive SQLite PRAGMA connection hooks."""
    database_url = "mysql+aiomysql://openeval:openeval@localhost:3306/openeval"
    engine = SimpleNamespace(sync_engine=object())
    create_engine = MagicMock(return_value=engine)
    listen = MagicMock()

    monkeypatch.setattr(
        session_mod,
        "get_settings",
        lambda: _settings(database_url),
    )
    monkeypatch.setattr(session_mod, "create_async_engine", create_engine)
    monkeypatch.setattr(session_mod.event, "listen", listen)

    assert session_mod.get_engine() is engine
    create_engine.assert_called_once_with(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
    )
    listen.assert_not_called()


def test_get_engine_uses_configured_mysql_pool_size(monkeypatch: pytest.MonkeyPatch) -> None:
    """MySQL engines should use the customer-info-style pool setting."""
    database_url = "mysql+aiomysql://openeval:openeval@localhost:3306/openeval"
    engine = SimpleNamespace(sync_engine=object())
    create_engine = MagicMock(return_value=engine)

    monkeypatch.setattr(
        session_mod,
        "get_settings",
        lambda: _settings(database_url, pool_size=12),
    )
    monkeypatch.setattr(session_mod, "create_async_engine", create_engine)

    assert session_mod.get_engine() is engine
    create_engine.assert_called_once_with(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=12,
    )


def test_get_engine_keeps_sqlite_pragma_for_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    """SQLite engines should still enable foreign-key enforcement."""
    database_url = "sqlite+aiosqlite://"
    engine = SimpleNamespace(sync_engine=object())
    create_engine = MagicMock(return_value=engine)
    listen = MagicMock()

    monkeypatch.setattr(
        session_mod,
        "get_settings",
        lambda: _settings(database_url),
    )
    monkeypatch.setattr(session_mod, "create_async_engine", create_engine)
    monkeypatch.setattr(session_mod.event, "listen", listen)

    assert session_mod.get_engine() is engine
    create_engine.assert_called_once_with(database_url, echo=False, pool_pre_ping=True)
    listen.assert_called_once_with(
        engine.sync_engine,
        "connect",
        session_mod._set_sqlite_pragma,
    )


def test_get_engine_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Engine creation should fail clearly when DATABASE_URL is missing."""
    monkeypatch.setattr(
        session_mod,
        "get_settings",
        lambda: _settings(""),
    )

    with pytest.raises(ValueError, match="DATABASE_URL or APP_MYSQL_CLIENT_DB must be set"):
        session_mod.get_engine()
