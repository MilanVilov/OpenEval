"""Add run heartbeats and unique persisted result keys.

Revision ID: 016
Revises: 015
"""

import sqlalchemy as sa

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add heartbeats to runs and deduplicate persisted result identity."""
    if not _has_column("eval_runs", "heartbeat_at"):
        op.add_column("eval_runs", sa.Column("heartbeat_at", sa.DateTime(), nullable=True))

    op.execute(
        "UPDATE eval_runs "
        "SET heartbeat_at = COALESCE(started_at, created_at) "
        "WHERE heartbeat_at IS NULL"
    )

    if not _has_unique_key("eval_results", "uq_eval_results_run_row", ["eval_run_id", "row_index"]):
        op.create_unique_constraint(
            "uq_eval_results_run_row",
            "eval_results",
            ["eval_run_id", "row_index"],
        )


def downgrade() -> None:
    """Remove the heartbeat column and result uniqueness constraint."""
    if _has_unique_key("eval_results", "uq_eval_results_run_row", ["eval_run_id", "row_index"]):
        op.drop_constraint("uq_eval_results_run_row", "eval_results", type_="unique")
    if _has_column("eval_runs", "heartbeat_at"):
        op.drop_column("eval_runs", "heartbeat_at")


def _has_column(table_name: str, column_name: str) -> bool:
    """Return whether ``table_name`` already has ``column_name``."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _has_unique_key(
    table_name: str,
    constraint_name: str,
    columns: list[str],
) -> bool:
    """Return whether the table already has the target unique key."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    unique_constraints = inspector.get_unique_constraints(table_name)
    for constraint in unique_constraints:
        if constraint.get("name") == constraint_name:
            return True
        if constraint.get("column_names") == columns:
            return True

    indexes = inspector.get_indexes(table_name)
    for index in indexes:
        if not index.get("unique"):
            continue
        if index.get("name") == constraint_name:
            return True
        if index.get("column_names") == columns:
            return True

    return False
