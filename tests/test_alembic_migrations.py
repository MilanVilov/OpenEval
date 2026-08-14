"""Tests for Alembic migration graph consistency."""

import ast
import importlib.util
from collections import Counter
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

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

    assert heads == ["023"]


def test_translation_cache_creation_uses_utf8mb4() -> None:
    """Fresh MySQL tables should support four-byte Unicode text."""
    migration = _load_migration("017_add_mapped_input_translation_cache.py")

    with patch.object(migration.op, "create_table") as create_table:
        migration.upgrade()

    create_kwargs = create_table.call_args.kwargs
    assert create_kwargs["mysql_charset"] == "utf8mb4"
    assert create_kwargs["mysql_collate"] == "utf8mb4_unicode_ci"


def test_translation_cache_unicode_repair_converts_existing_mysql_table() -> None:
    """Existing MySQL cache columns should be converted without changing nullability."""
    migration = _load_migration("021_ensure_translation_cache_utf8mb4.py")
    mysql_context = SimpleNamespace(dialect=SimpleNamespace(name="mysql"))

    with (
        patch.object(migration.op, "get_context", return_value=mysql_context),
        patch.object(migration.op, "execute") as execute,
    ):
        migration.upgrade()

    assert [call.args[0] for call in execute.call_args_list] == [
        "ALTER TABLE mapped_input_translations "
        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
        "ALTER TABLE mapped_input_translations "
        "MODIFY source_text LONGTEXT "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL",
        "ALTER TABLE mapped_input_translations "
        "MODIFY translated_text LONGTEXT "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL",
    ]


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


def _load_migration(filename: str) -> ModuleType:
    """Load one migration module from the versions directory."""
    migration_path = MIGRATIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(migration_path.stem, migration_path)
    assert spec is not None and spec.loader is not None

    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


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

    if (
        isinstance(statement, ast.AnnAssign)
        and isinstance(statement.target, ast.Name)
        and statement.target.id == variable_name
    ):
        return statement.value

    return None


def _is_revision_value(value: object) -> bool:
    """Return whether a value is valid Alembic revision metadata."""
    if isinstance(value, str) or value is None:
        return True

    return isinstance(value, tuple) and all(isinstance(item, str) for item in value)
