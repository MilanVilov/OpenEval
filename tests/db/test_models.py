"""Tests for database model metadata."""

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from src.db.models import EvalConfig, EvalResult


def test_eval_config_system_prompt_uses_mysql_longtext() -> None:
    """MySQL config prompts should store model-context-sized text."""
    ddl = str(CreateTable(EvalConfig.__table__).compile(dialect=mysql.dialect()))

    assert "system_prompt LONGTEXT" in ddl


def test_eval_result_input_uses_mysql_longtext() -> None:
    """MySQL evaluation results should store large dataset inputs."""
    ddl = str(CreateTable(EvalResult.__table__).compile(dialect=mysql.dialect()))

    assert "input_data LONGTEXT" in ddl
