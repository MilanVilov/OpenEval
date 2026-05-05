"""Add comparer_weights to eval_configs.

Revision ID: 007
Revises: 006
"""

import sqlalchemy as sa

from alembic import op

revision = "007"
down_revision = "006"


def upgrade() -> None:
    op.add_column(
        "eval_configs",
        sa.Column("comparer_weights", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("eval_configs", "comparer_weights")
