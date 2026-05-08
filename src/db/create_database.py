"""Create the configured MySQL database before running migrations."""

from __future__ import annotations

import asyncio
from typing import Any

import aiomysql

from src.config import (
    MYSQL_DEFAULTS_GROUP,
    MYSQL_DEFAULTS_USER,
    Settings,
    get_settings,
    mysql_defaults_file,
)


async def create_mysql_database(settings: Settings | None = None) -> str:
    """Create the configured MySQL database if it does not already exist."""
    settings = settings or get_settings()
    database = settings.app_mysql_client_db
    if not database:
        raise ValueError("APP_MYSQL_CLIENT_DB must be set")

    connection = await aiomysql.connect(**_connection_kwargs(settings))
    try:
        async with connection.cursor() as cursor:
            await cursor.execute(_create_database_sql(database))
        await connection.commit()
    finally:
        connection.close()
        await connection.wait_closed()

    return database


def main() -> None:
    """Run the database creation command."""
    database = asyncio.run(create_mysql_database())
    print(f"Database {database!r} is ready.")


def _connection_kwargs(settings: Settings) -> dict[str, Any]:
    """Return aiomysql connection arguments without selecting a database."""
    defaults_file = mysql_defaults_file()
    if defaults_file.exists():
        return {
            "read_default_file": str(defaults_file),
            "read_default_group": MYSQL_DEFAULTS_GROUP,
            "user": MYSQL_DEFAULTS_USER,
        }

    return {
        "host": settings.app_mysql_client_host,
        "port": settings.app_mysql_client_port,
        "user": settings.app_mysql_client_user,
        "password": settings.app_mysql_client_pass,
    }


def _create_database_sql(database: str) -> str:
    """Return SQL for creating a UTF-8 MySQL database."""
    return (
        f"CREATE DATABASE IF NOT EXISTS {_quote_identifier(database)} "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )


def _quote_identifier(identifier: str) -> str:
    """Quote a MySQL identifier."""
    return f"`{identifier.replace('`', '``')}`"
