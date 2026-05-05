"""Add custom_graders JSON column to eval_configs."""

import sqlalchemy as sa

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("eval_configs", sa.Column("custom_graders", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("eval_configs", "custom_graders")
