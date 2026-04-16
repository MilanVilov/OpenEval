"""Unify comparers and custom graders into single graders column.

Drops comparer_type, comparer_config, comparer_weights columns.
Renames custom_graders to graders.

Revision ID: 008
Revises: 007
"""

import sqlalchemy as sa
from alembic import op

revision = "008"
down_revision = "007"


def upgrade() -> None:
    # Rename custom_graders -> graders
    with op.batch_alter_table("eval_configs") as batch_op:
        batch_op.alter_column("custom_graders", new_column_name="graders")
        batch_op.drop_column("comparer_type")
        batch_op.drop_column("comparer_config")
        batch_op.drop_column("comparer_weights")


def downgrade() -> None:
    with op.batch_alter_table("eval_configs") as batch_op:
        batch_op.alter_column("graders", new_column_name="custom_graders")
        batch_op.add_column(
            sa.Column("comparer_type", sa.String(), nullable=True, server_default="exact_match")
        )
        batch_op.add_column(
            sa.Column("comparer_config", sa.JSON(), nullable=True, server_default="{}")
        )
        batch_op.add_column(
            sa.Column("comparer_weights", sa.JSON(), nullable=True, server_default="{}")
        )
