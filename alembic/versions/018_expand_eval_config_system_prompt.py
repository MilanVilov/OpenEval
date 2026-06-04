"""Expand eval config system prompts for large OpenAI context windows.

Revision ID: 018
Revises: 017
"""

from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert eval config system prompts to LONGTEXT on MySQL."""
    if op.get_context().dialect.name != "mysql":
        return

    op.execute(
        "ALTER TABLE eval_configs "
        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    op.execute(
        "ALTER TABLE eval_configs "
        "MODIFY system_prompt LONGTEXT "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL"
    )


def downgrade() -> None:
    """Keep LONGTEXT in place to avoid truncating stored prompts."""
