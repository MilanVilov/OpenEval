"""Add cached mapped input translations.

Revision ID: 017
Revises: 016
"""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mapped_input_translations",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("target_language", sa.String(length=100), nullable=False),
        sa.Column(
            "source_text",
            sa.Text().with_variant(mysql.LONGTEXT(), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "translated_text",
            sa.Text().with_variant(mysql.LONGTEXT(), "mysql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "cache_key",
            name="uq_mapped_input_translations_cache_key",
        ),
    )


def downgrade() -> None:
    op.drop_table("mapped_input_translations")
