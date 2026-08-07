"""Ensure translation cache text supports four-byte Unicode.

Revision ID: 021
Revises: 020
"""

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None

TEXT_COLUMNS = ("source_text", "translated_text")


def upgrade() -> None:
    """Convert translation cache text columns to utf8mb4 on MySQL."""
    if op.get_context().dialect.name != "mysql":
        return

    op.execute(
        "ALTER TABLE mapped_input_translations "
        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    for column in TEXT_COLUMNS:
        op.execute(
            "ALTER TABLE mapped_input_translations "
            f"MODIFY {column} LONGTEXT "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL"
        )


def downgrade() -> None:
    """Keep utf8mb4 in place to avoid breaking cached Unicode text."""
