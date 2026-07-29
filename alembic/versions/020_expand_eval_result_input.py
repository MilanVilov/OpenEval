"""Expand evaluation result inputs for large dataset fields.

Revision ID: 020
Revises: 019
"""

from alembic import op

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert evaluation result inputs to LONGTEXT on MySQL."""
    if op.get_context().dialect.name != "mysql":
        return

    op.execute(
        "ALTER TABLE eval_results "
        "MODIFY input_data LONGTEXT "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL"
    )


def downgrade() -> None:
    """Keep LONGTEXT in place to avoid truncating stored inputs."""
