"""Add tags JSON column to eval_configs."""

import sqlalchemy as sa

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("eval_configs", sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("eval_configs", "tags")
