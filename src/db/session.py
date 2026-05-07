"""Async SQLAlchemy engine and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from src.config import Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key enforcement for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _is_sqlite_url(database_url: str) -> bool:
    """Return whether a database URL targets SQLite."""
    return make_url(database_url).get_backend_name() == "sqlite"


def _get_database_url(settings: Settings | None = None) -> str:
    """Return the configured database URL or raise a clear configuration error."""
    settings = settings or get_settings()
    database_url = settings.database_url or settings.resolved_database_url()
    if not database_url:
        raise ValueError("DATABASE_URL or APP_MYSQL_CLIENT_DB must be set")
    return database_url


def _get_engine_kwargs(database_url: str, settings: Settings) -> dict[str, object]:
    """Return SQLAlchemy engine options for the configured database."""
    kwargs: dict[str, object] = {"echo": False, "pool_pre_ping": True}
    if not _is_sqlite_url(database_url):
        kwargs["pool_size"] = settings.app_db_connection_pool
    return kwargs


def get_engine() -> AsyncEngine:
    """Return the async engine, creating it lazily on first call."""
    global _engine
    if _engine is None:
        settings = get_settings()
        database_url = _get_database_url(settings)
        _engine = create_async_engine(database_url, **_get_engine_kwargs(database_url, settings))
        if _is_sqlite_url(database_url):
            event.listen(_engine.sync_engine, "connect", _set_sqlite_pragma)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory, creating it lazily on first call."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Yield an async database session for FastAPI ``Depends()``."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession]:
    """Async context manager for sessions outside of FastAPI Depends().

    Use this in background tasks, CLI scripts, etc.
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session
