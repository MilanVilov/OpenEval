"""Add reasoning_config and response_format to eval_configs."""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("eval_configs", sa.Column("reasoning_config", sa.JSON(), nullable=True))
    op.add_column("eval_configs", sa.Column("response_format", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("eval_configs", "response_format")
    op.drop_column("eval_configs", "reasoning_config")
