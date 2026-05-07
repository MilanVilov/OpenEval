"""Tests for application settings loading."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.config import Settings


def test_settings_ignore_compose_mysql_variables(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Compose-only MySQL variables should not break app settings loading."""
    monkeypatch.setenv("HOME", str(tmp_path))
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/openeval",
                "MYSQL_DATABASE=openeval",
                "MYSQL_USER=openeval",
                "MYSQL_PASSWORD=openeval",
                "MYSQL_ROOT_PASSWORD=openeval_root",
                "MYSQL_PORT=3306",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.database_url == "mysql+aiomysql://user:pass@localhost:3306/openeval"
    assert settings.resolved_database_url() == settings.database_url


def test_settings_build_database_url_from_app_mysql_client_variables(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Customer-info-style MySQL variables should produce a database URL."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "APP_MYSQL_CLIENT_DB=open/eval",
                "APP_MYSQL_CLIENT_HOST=mysql.local",
                "APP_MYSQL_CLIENT_PORT=3307",
                "APP_MYSQL_CLIENT_USER=open eval",
                "APP_MYSQL_CLIENT_PASS=p@ss word",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert (
        settings.resolved_database_url()
        == "mysql+aiomysql://open%20eval:p%40ss%20word@mysql.local:3307/open%2Feval"
    )


def test_settings_use_mysql_defaults_file_when_present(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A local MySQL defaults file should be used like customer-info does."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    defaults_file = tmp_path / ".my.cnf"
    defaults_file.write_text("[client]\npassword=secret\n", encoding="utf-8")
    env_file = tmp_path / ".env"
    env_file.write_text("APP_MYSQL_CLIENT_DB=openeval\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)
    parsed_url = urlparse(settings.resolved_database_url())
    query = parse_qs(parsed_url.query)

    assert parsed_url.scheme == "mysql+aiomysql"
    assert parsed_url.username == "customer_info"
    assert parsed_url.path == "/openeval"
    assert query == {
        "read_default_file": [str(defaults_file)],
        "read_default_group": ["client"],
    }
