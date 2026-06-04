"""Tests for Alembic migration graph consistency."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def test_alembic_revisions_are_unique() -> None:
    """Every migration file must declare a unique Alembic revision."""
    revisions = _load_revision_ids()
    revision_counts = Counter(revisions.values())

    duplicates = sorted(
        revision
        for revision, count in revision_counts.items()
        if count > 1
    )

    assert duplicates == []


def test_alembic_has_single_head() -> None:
    """The migration graph should have exactly one latest head."""
    revisions = _load_revision_ids()
    down_revisions = {
        value
        for value in _load_revision_values("down_revision").values()
        if isinstance(value, str)
    }

    heads = sorted(set(revisions.values()) - down_revisions)

    assert heads == ["018"]


def _load_revision_ids() -> dict[Path, str]:
    """Load required Alembic revision identifiers from migration files."""
    revisions = _load_revision_values("revision")
    missing_revisions = sorted(
        migration_path.name
        for migration_path, revision in revisions.items()
        if not isinstance(revision, str)
    )

    assert missing_revisions == []

    return {
        migration_path: revision
        for migration_path, revision in revisions.items()
        if isinstance(revision, str)
    }


def _load_revision_values(variable_name: str) -> dict[Path, str | tuple[str, ...] | None]:
    """Load Alembic metadata assignment values from migration files."""
    values: dict[Path, str | tuple[str, ...] | None] = {}

    for migration_path in sorted(MIGRATIONS_DIR.glob("*.py")):
        module = ast.parse(migration_path.read_text(encoding="utf-8"))
        values[migration_path] = _find_assignment_value(module, variable_name)

    return values


def _find_assignment_value(
    module: ast.Module,
    variable_name: str,
) -> str | tuple[str, ...] | None:
    """Return the literal value assigned to a module-level variable."""
    for statement in module.body:
        value_node = _get_assignment_value_node(statement, variable_name)
        if value_node is None:
            continue

        value = ast.literal_eval(value_node)
        if _is_revision_value(value):
            return value

    return None


def _get_assignment_value_node(
    statement: ast.stmt,
    variable_name: str,
) -> ast.expr | None:
    """Return the AST value node for a module-level assignment."""
    if isinstance(statement, ast.Assign):
        has_target = any(
            isinstance(target, ast.Name) and target.id == variable_name
            for target in statement.targets
        )
        return statement.value if has_target else None

    if isinstance(statement, ast.AnnAssign):
        if isinstance(statement.target, ast.Name) and statement.target.id == variable_name:
            return statement.value

    return None


def _is_revision_value(value: object) -> bool:
    """Return whether a value is valid Alembic revision metadata."""
    if isinstance(value, str) or value is None:
        return True

    return isinstance(value, tuple) and all(isinstance(item, str) for item in value)
