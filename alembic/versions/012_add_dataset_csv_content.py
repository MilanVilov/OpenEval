"""Add CSV content snapshots to datasets.

Revision ID: 012
Revises: 011
"""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "datasets",
        sa.Column(
            "csv_content",
            sa.Text().with_variant(mysql.LONGTEXT(), "mysql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("datasets", "csv_content")
