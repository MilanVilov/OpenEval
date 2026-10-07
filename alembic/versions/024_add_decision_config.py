"""Add Decisions API question configuration.

Revision ID: 024
Revises: 023
"""

import sqlalchemy as sa

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Store Decisions questions on evaluation configurations."""
    op.add_column("eval_configs", sa.Column("decision_config", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove Decisions question configuration."""
    op.drop_column("eval_configs", "decision_config")
