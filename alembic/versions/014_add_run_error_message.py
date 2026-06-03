"""Add run-level failure messages.

Revision ID: 014
Revises: 013
"""

from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a nullable error message column to eval runs."""
    op.add_column("eval_runs", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove the run-level error message column."""
    op.drop_column("eval_runs", "error_message")
