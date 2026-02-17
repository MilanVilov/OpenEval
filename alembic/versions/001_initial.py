"""Initial schema — create all tables.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create eval_configs, datasets, vector_stores, eval_runs, and eval_results tables."""
    op.create_table(
        "eval_configs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("tools", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tool_options", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("comparer_type", sa.String(), nullable=False),
        sa.Column("comparer_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("concurrency", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "datasets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "vector_stores",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("openai_vector_store_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(), nullable=False, server_default="'creating'"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "eval_config_id",
            sa.String(),
            sa.ForeignKey("eval_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            sa.String(),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="'pending'"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_eval_runs_eval_config_id", "eval_runs", ["eval_config_id"])
    op.create_index("ix_eval_runs_dataset_id", "eval_runs", ["dataset_id"])

    op.create_table(
        "eval_results",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "eval_run_id",
            sa.String(),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("input_data", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("actual_output", sa.Text(), nullable=True),
        sa.Column("comparer_score", sa.Float(), nullable=True),
        sa.Column("comparer_details", sa.JSON(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_eval_results_eval_run_id", "eval_results", ["eval_run_id"])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("vector_stores")
    op.drop_table("datasets")
    op.drop_table("eval_configs")
