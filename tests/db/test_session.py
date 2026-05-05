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


def test_get_engine_skips_sqlite_pragma_for_mysql(monkeypatch: pytest.MonkeyPatch) -> None:
    """MySQL engines should not receive SQLite PRAGMA connection hooks."""
    database_url = "mysql+aiomysql://openeval:openeval@localhost:3306/openeval"
    engine = SimpleNamespace(sync_engine=object())
    create_engine = MagicMock(return_value=engine)
    listen = MagicMock()

    monkeypatch.setattr(
        session_mod,
        "get_settings",
        lambda: SimpleNamespace(database_url=database_url),
    )
    monkeypatch.setattr(session_mod, "create_async_engine", create_engine)
    monkeypatch.setattr(session_mod.event, "listen", listen)

    assert session_mod.get_engine() is engine
    create_engine.assert_called_once_with(database_url, echo=False, pool_pre_ping=True)
    listen.assert_not_called()


def test_get_engine_keeps_sqlite_pragma_for_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    """SQLite engines should still enable foreign-key enforcement."""
    database_url = "sqlite+aiosqlite://"
    engine = SimpleNamespace(sync_engine=object())
    create_engine = MagicMock(return_value=engine)
    listen = MagicMock()

    monkeypatch.setattr(
        session_mod,
        "get_settings",
        lambda: SimpleNamespace(database_url=database_url),
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
