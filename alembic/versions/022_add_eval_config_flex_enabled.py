"""Add Flex processing selection to evaluation configurations.

Revision ID: 022
Revises: 021
"""

import sqlalchemy as sa

from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the Flex processing flag with a disabled default."""
    op.add_column(
        "eval_configs",
        sa.Column("flex_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Remove the Flex processing flag."""
    op.drop_column("eval_configs", "flex_enabled")
