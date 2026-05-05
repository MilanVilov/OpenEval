"""Add schedules table and scheduled_by_id on eval_runs.

Revision ID: 009
Revises: 008
"""

import sqlalchemy as sa

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "schedules",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "eval_config_id",
            sa.String(length=32),
            sa.ForeignKey("eval_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            sa.String(length=32),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cron_expression", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("slack_webhook_url", sa.String(length=2048), nullable=True),
        sa.Column("min_accuracy", sa.Float(), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    with op.batch_alter_table("eval_runs") as batch_op:
        batch_op.add_column(sa.Column("scheduled_by_id", sa.String(length=32), nullable=True))
        batch_op.create_foreign_key(
            "fk_eval_runs_scheduled_by_id",
            "schedules",
            ["scheduled_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_eval_runs_scheduled_by_id", ["scheduled_by_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("eval_runs") as batch_op:
        batch_op.drop_index("ix_eval_runs_scheduled_by_id")
        batch_op.drop_constraint("fk_eval_runs_scheduled_by_id", type_="foreignkey")
        batch_op.drop_column("scheduled_by_id")
    op.drop_table("schedules")
