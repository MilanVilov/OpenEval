"""Tests for database model metadata."""

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from src.db.models import EvalConfig


def test_eval_config_system_prompt_uses_mysql_longtext() -> None:
    """MySQL config prompts should store model-context-sized text."""
    ddl = str(CreateTable(EvalConfig.__table__).compile(dialect=mysql.dialect()))

    assert "system_prompt LONGTEXT" in ddl
