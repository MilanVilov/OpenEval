"""Add optional comment to eval configs.

Revision ID: 019
Revises: 018
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable human comment metadata to eval configs."""
    op.add_column(
        "eval_configs",
        sa.Column("comment", sa.Text().with_variant(mysql.LONGTEXT(), "mysql"), nullable=True),
    )


def downgrade() -> None:
    """Remove human comment metadata from eval configs."""
    op.drop_column("eval_configs", "comment")
