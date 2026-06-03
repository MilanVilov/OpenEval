"""Add run heartbeats and unique persisted result keys.

Revision ID: 015
Revises: 014
"""

import sqlalchemy as sa

from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add heartbeats to runs and deduplicate persisted result identity."""
    op.add_column("eval_runs", sa.Column("heartbeat_at", sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE eval_runs "
        "SET heartbeat_at = COALESCE(started_at, created_at) "
        "WHERE heartbeat_at IS NULL"
    )
    op.create_unique_constraint(
        "uq_eval_results_run_row",
        "eval_results",
        ["eval_run_id", "row_index"],
    )


def downgrade() -> None:
    """Remove the heartbeat column and result uniqueness constraint."""
    op.drop_constraint("uq_eval_results_run_row", "eval_results", type_="unique")
    op.drop_column("eval_runs", "heartbeat_at")
