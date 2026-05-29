"""Ensure dataset CSV snapshots support 4-byte Unicode.

Revision ID: 013
Revises: 012
"""

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert dataset CSV snapshots to utf8mb4 on MySQL."""
    if op.get_context().dialect.name != "mysql":
        return

    op.execute(
        "ALTER TABLE datasets "
        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    op.execute(
        "ALTER TABLE datasets "
        "MODIFY csv_content LONGTEXT "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL"
    )


def downgrade() -> None:
    """Keep utf8mb4 in place to avoid breaking stored Unicode data."""
