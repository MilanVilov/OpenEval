"""Move Flex processing selection from configurations to runs.

Revision ID: 023
Revises: 022
"""

import sqlalchemy as sa

from alembic import op

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store the Flex processing selection on individual runs."""
    op.add_column(
        "eval_runs",
        sa.Column("flex_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_column("eval_configs", "flex_enabled")


def downgrade() -> None:
    """Restore the configuration-level Flex processing selection."""
    op.add_column(
        "eval_configs",
        sa.Column("flex_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_column("eval_runs", "flex_enabled")
