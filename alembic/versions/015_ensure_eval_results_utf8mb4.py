"""Ensure eval result text supports 4-byte Unicode.

Revision ID: 015
Revises: 014
"""

from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None

TEXT_COLUMNS = (
    ("input_data", "NOT NULL"),
    ("expected_output", "NOT NULL"),
    ("actual_output", "NULL"),
    ("error", "NULL"),
)


def upgrade() -> None:
    """Convert eval result text columns to utf8mb4 on MySQL."""
    if op.get_context().dialect.name != "mysql":
        return

    op.execute(
        "ALTER TABLE eval_results "
        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    for column, nullability in TEXT_COLUMNS:
        op.execute(
            "ALTER TABLE eval_results "
            f"MODIFY {column} TEXT "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci {nullability}"
        )


def downgrade() -> None:
    """Keep utf8mb4 in place to avoid breaking stored Unicode data."""
