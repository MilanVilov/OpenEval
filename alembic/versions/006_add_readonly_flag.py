"""Add readonly flag to eval_configs.

Revision ID: 006
Revises: 005
"""

import sqlalchemy as sa

from alembic import op

revision = "006"
down_revision = "005"


def upgrade() -> None:
    op.add_column(
        "eval_configs",
        sa.Column("readonly", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("eval_configs", "readonly")
