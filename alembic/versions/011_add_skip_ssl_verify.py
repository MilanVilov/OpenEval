"""Add skip_ssl_verify flag to data_sources.

Revision ID: 011
Revises: 010
"""

import sqlalchemy as sa

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "data_sources",
        sa.Column("skip_ssl_verify", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("data_sources", "skip_ssl_verify")
