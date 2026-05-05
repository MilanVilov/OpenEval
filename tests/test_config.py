"""Tests for application settings loading."""

from pathlib import Path

from src.config import Settings


def test_settings_ignore_compose_mysql_variables(tmp_path: Path) -> None:
    """Compose-only MySQL variables should not break app settings loading."""
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
