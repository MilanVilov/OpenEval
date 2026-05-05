"""Unify comparers and custom graders into single graders column.

Converts existing comparer_type + comparer_weights + custom_graders data
into the new unified graders JSON column, then drops the old columns.

Revision ID: 008
Revises: 007
"""

import json

import sqlalchemy as sa

from alembic import op

revision = "008"
down_revision = "007"

# Mapping from old built-in comparer names to new grader type/config
_COMPARER_TO_GRADER = {
    "semantic_similarity": {
        "type": "semantic_similarity",
        "threshold": 0.8,
    },
    "json_schema_match": {
        "type": "json_schema",
        "threshold": 1.0,
    },
    "json_field_match": {
        "type": "json_field",
        "threshold": 0.7,
    },
    # exact_match, pattern_match, llm_judge are removed — skipped
}


def upgrade() -> None:  # noqa: C901
    conn = op.get_bind()

    # Step 1: Add new graders column alongside old columns
    with op.batch_alter_table("eval_configs") as batch_op:
        batch_op.add_column(sa.Column("graders", sa.JSON(), nullable=True))

    # Step 2: Migrate data — convert old columns into graders JSON
    rows = conn.execute(
        sa.text("SELECT id, comparer_type, comparer_weights, custom_graders FROM eval_configs")
    ).fetchall()

    for row in rows:
        config_id = row[0]
        comparer_type_str = row[1] or ""
        weights_raw = row[2]
        custom_graders_raw = row[3]

        # Parse JSON columns (may be string or already dict depending on driver)
        if isinstance(weights_raw, str):
            weights = json.loads(weights_raw) if weights_raw else {}
        else:
            weights = weights_raw or {}

        if isinstance(custom_graders_raw, str):
            custom_graders = json.loads(custom_graders_raw) if custom_graders_raw else []
        else:
            custom_graders = custom_graders_raw or []

        graders: list[dict] = []

        # Convert built-in comparers that map to new grader types
        if comparer_type_str:
            for ct in comparer_type_str.split(","):
                ct = ct.strip()
                if ct in _COMPARER_TO_GRADER:
                    grader = {
                        "name": ct,
                        **_COMPARER_TO_GRADER[ct],
                    }
                    w = weights.get(ct)
                    if w is not None:
                        grader["weight"] = w
                    graders.append(grader)
                # exact_match, pattern_match, llm_judge are dropped

        # Carry over existing custom graders with their weights
        for cg in custom_graders:
            grader = {**cg}
            cg_name = cg.get("name", "").strip()
            w = weights.get(f"custom:{cg_name}")
            if w is not None:
                grader["weight"] = w
            graders.append(grader)

        conn.execute(
            sa.text("UPDATE eval_configs SET graders = :graders WHERE id = :id"),
            {"graders": json.dumps(graders), "id": config_id},
        )

    # Step 3: Drop old columns
    with op.batch_alter_table("eval_configs") as batch_op:
        batch_op.drop_column("custom_graders")
        batch_op.drop_column("comparer_type")
        batch_op.drop_column("comparer_config")
        batch_op.drop_column("comparer_weights")


def downgrade() -> None:
    with op.batch_alter_table("eval_configs") as batch_op:
        batch_op.add_column(sa.Column("custom_graders", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "comparer_type",
                sa.String(length=255),
                nullable=False,
                server_default="exact_match",
            )
        )
        batch_op.add_column(sa.Column("comparer_config", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("comparer_weights", sa.JSON(), nullable=True))

    # Best-effort: move graders back into custom_graders
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, graders FROM eval_configs")).fetchall()

    for row in rows:
        config_id = row[0]
        graders_raw = row[1]
        if isinstance(graders_raw, str):
            graders = json.loads(graders_raw) if graders_raw else []
        else:
            graders = graders_raw or []

        conn.execute(
            sa.text("UPDATE eval_configs SET custom_graders = :cg WHERE id = :id"),
            {"cg": json.dumps(graders), "id": config_id},
        )

    with op.batch_alter_table("eval_configs") as batch_op:
        batch_op.drop_column("graders")
