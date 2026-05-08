"""Add remote data sources, import presets, and dataset import metadata.

Revision ID: 010
Revises: 009
"""

import sqlalchemy as sa

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_sources",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("auth_type", sa.String(length=50), nullable=False),
        sa.Column("query_params", sa.JSON(), nullable=False),
        sa.Column("request_body", sa.JSON(), nullable=True),
        sa.Column("headers", sa.JSON(), nullable=False),
        sa.Column("encrypted_secrets", sa.Text(), nullable=True),
        sa.Column("pagination_mode", sa.String(length=50), nullable=False),
        sa.Column("pagination_config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "import_presets",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column(
            "data_source_id",
            sa.String(length=32),
            sa.ForeignKey("data_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("records_path", sa.String(length=1024), nullable=False),
        sa.Column("field_mapping", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_import_presets_data_source_id",
        "import_presets",
        ["data_source_id"],
        unique=False,
    )

    with op.batch_alter_table("datasets") as batch_op:
        batch_op.add_column(sa.Column("import_preset_id", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("import_source_snapshot", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_datasets_import_preset_id",
            "import_presets",
            ["import_preset_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_datasets_import_preset_id", ["import_preset_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.drop_index("ix_datasets_import_preset_id")
        batch_op.drop_constraint("fk_datasets_import_preset_id", type_="foreignkey")
        batch_op.drop_column("import_source_snapshot")
        batch_op.drop_column("import_preset_id")

    op.drop_index("ix_import_presets_data_source_id", table_name="import_presets")
    op.drop_table("import_presets")
    op.drop_table("data_sources")
