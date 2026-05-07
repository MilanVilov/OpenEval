"""Application configuration via Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote, urlencode

from pydantic_settings import BaseSettings

MYSQL_DEFAULTS_FILE = "~/.my.cnf"
MYSQL_DEFAULTS_GROUP = "client"
MYSQL_DEFAULTS_USER = "customer_info"
MYSQL_DRIVER = "mysql+aiomysql"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    openai_api_key: str = ""
    database_url: str = ""
    app_db_connection_pool: int = 5
    app_mysql_client_db: str = ""
    app_mysql_client_host: str = "127.0.0.1"
    app_mysql_client_port: int = 3306
    app_mysql_client_user: str = "root"
    app_mysql_client_pass: str = ""
    upload_dir: str = "./data/uploads"
    default_concurrency: int = 5
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173"
    slack_webhook_url: str = ""
    app_base_url: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def resolved_database_url(self) -> str:
        """Return the explicit database URL or build one from MySQL client settings."""
        if self.database_url:
            return self.database_url
        if not self.app_mysql_client_db:
            return ""
        if _mysql_defaults_file().exists():
            return _build_mysql_defaults_url(self.app_mysql_client_db)
        return _build_mysql_client_url(self)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


def _mysql_defaults_file() -> Path:
    """Return the MySQL defaults file path used by customer-info."""
    return Path(MYSQL_DEFAULTS_FILE).expanduser()


def _build_mysql_defaults_url(database: str) -> str:
    """Build a MySQL URL that reads host and credentials from ``~/.my.cnf``."""
    query = urlencode(
        {
            "read_default_file": str(_mysql_defaults_file()),
            "read_default_group": MYSQL_DEFAULTS_GROUP,
        }
    )
    return f"{MYSQL_DRIVER}://{MYSQL_DEFAULTS_USER}@/{_quote_url_part(database)}?{query}"


def _build_mysql_client_url(settings: Settings) -> str:
    """Build a MySQL URL from customer-info-style ``APP_MYSQL_CLIENT_*`` settings."""
    user = _quote_url_part(settings.app_mysql_client_user)
    password = _quote_url_part(settings.app_mysql_client_pass)
    auth = f"{user}:{password}" if password else user
    database = _quote_url_part(settings.app_mysql_client_db)
    return (
        f"{MYSQL_DRIVER}://{auth}@{settings.app_mysql_client_host}:"
        f"{settings.app_mysql_client_port}/{database}"
    )


def _quote_url_part(value: str) -> str:
    """Quote one URL component without treating any character as safe."""
    return quote(value, safe="")
