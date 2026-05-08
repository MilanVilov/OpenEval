"""Tests for async database session setup."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

import src.db.create_database as create_database_mod
import src.db.session as session_mod
from src.config import Settings


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


class FakeCursor:
    """Async cursor fake that records executed SQL."""

    def __init__(self) -> None:
        self.sql = ""

    async def __aenter__(self) -> "FakeCursor":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, sql: str) -> None:
        """Record the executed SQL."""
        self.sql = sql


class FakeConnection:
    """Async connection fake that records cleanup calls."""

    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.committed = False
        self.closed = False
        self.waited_closed = False

    def cursor(self) -> FakeCursor:
        """Return the fake cursor."""
        return self.cursor_instance

    async def commit(self) -> None:
        """Record that the transaction was committed."""
        self.committed = True

    def close(self) -> None:
        """Record that close was called."""
        self.closed = True

    async def wait_closed(self) -> None:
        """Record that the connection was fully closed."""
        self.waited_closed = True


async def test_create_mysql_database_uses_client_settings(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Database creation should connect with APP_MYSQL_CLIENT settings."""
    connection = FakeConnection()
    connect = MagicMock()

    async def fake_connect(**kwargs: Any) -> FakeConnection:
        connect(**kwargs)
        return connection

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(create_database_mod.aiomysql, "connect", fake_connect)
    settings = Settings(
        app_mysql_client_db="open`eval",
        app_mysql_client_host="mysql.local",
        app_mysql_client_port=3307,
        app_mysql_client_user="openeval",
        app_mysql_client_pass="secret",
    )

    database = await create_database_mod.create_mysql_database(settings)

    assert database == "open`eval"
    connect.assert_called_once_with(
        host="mysql.local",
        port=3307,
        user="openeval",
        password="secret",
    )
    assert "CREATE DATABASE IF NOT EXISTS `open``eval`" in connection.cursor_instance.sql
    assert connection.committed is True
    assert connection.closed is True
    assert connection.waited_closed is True


async def test_create_mysql_database_uses_defaults_file(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Database creation should prefer ~/.my.cnf when it exists."""
    connection = FakeConnection()
    connect = MagicMock()
    defaults_file = tmp_path / ".my.cnf"
    defaults_file.write_text("[client]\npassword=secret\n", encoding="utf-8")

    async def fake_connect(**kwargs: Any) -> FakeConnection:
        connect(**kwargs)
        return connection

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(create_database_mod.aiomysql, "connect", fake_connect)
    settings = Settings(app_mysql_client_db="openeval")

    await create_database_mod.create_mysql_database(settings)

    connect.assert_called_once_with(
        read_default_file=str(defaults_file),
        read_default_group="client",
        user="customer_info",
    )
    assert "CREATE DATABASE IF NOT EXISTS `openeval`" in connection.cursor_instance.sql
