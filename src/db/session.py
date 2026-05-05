"""Async SQLAlchemy engine and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from src.config import get_settings

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


def get_engine() -> AsyncEngine:
    """Return the async engine, creating it lazily on first call."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
        if _is_sqlite_url(settings.database_url):
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
