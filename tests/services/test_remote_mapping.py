"""Tests for remote payload mapping helpers."""

from src.services.remote_mapping import (
    extract_records,
    find_array_paths,
    list_field_candidates,
    map_records,
    resolve_path,
)


def test_find_array_paths_and_extract_records_nested_payload() -> None:
    """Nested lists should be discoverable and extractable by path."""
    payload = {
        "data": {
            "items": [
                {"question": "q1", "answer": "a1", "tags": ["x", "y"]},
                {"question": "q2", "answer": "a2", "tags": ["z"]},
            ]
        }
    }

    assert "$.data.items" in find_array_paths(payload)
    assert "$.data.items[].tags" in find_array_paths(payload)
    assert resolve_path(payload, "$.data.items[1].answer") == "a2"
    assert resolve_path(payload, "$.data.items[].answer") == ["a1", "a2"]
    assert extract_records(payload, "$.data.items") == payload["data"]["items"]
    assert extract_records(payload, "$.data.items[].tags") == ["x", "y", "z"]


def test_map_records_serializes_nested_values_and_missing_fields() -> None:
    """Mapping should stringify nested values and blank missing fields."""
    records = [
        {"question": "q1", "answer": {"value": "a1"}, "tags": ["x", "y"]},
        {"question": "q2"},
    ]

    rows = map_records(
        records,
        {
            "input": "question",
            "expected_output": "answer.value",
            "labels": "tags",
            "missing": "unknown.field",
        },
    )

    assert rows[0]["input"] == "q1"
    assert rows[0]["expected_output"] == "a1"
    assert rows[0]["labels"] == '["x","y"]'
    assert rows[0]["missing"] == ""
    assert rows[1]["expected_output"] == ""


def test_map_records_supports_simple_template_interpolation() -> None:
    """Mapping values may interpolate multiple record paths into one string."""
    records = [
        {
            "title": "Mango Salsa Chicken",
            "difficulty": "Easy",
            "ingredients": ["Chicken thighs", "Mango"],
            "steps": [{"text": "Season the chicken"}, {"text": "Bake until cooked"}],
        }
    ]

    rows = map_records(
        records,
        {
            "input": "Recipe: {title}\nDifficulty: {difficulty}\nIngredients: {ingredients}",
            "expected_output": "{steps[0].text} Then {steps[1].text}",
        },
    )

    assert rows[0]["input"] == 'Recipe: Mango Salsa Chicken\nDifficulty: Easy\nIngredients: ["Chicken thighs","Mango"]'
    assert rows[0]["expected_output"] == "Season the chicken Then Bake until cooked"


def test_map_records_supports_conditional_mapping_expressions() -> None:
    """Conditional expressions may compare resolved values and choose branches."""
    records = [
        {
            "mode": "Day",
            "steps": [{"text": "Day"}, {"text": "Bake"}],
        },
        {
            "mode": "Night",
            "steps": [{"text": "Sleep"}],
        },
    ]

    rows = map_records(
        records,
        {
            "input": '{mode == "Day" ? "Wake" : "Rest"}',
            "expected_output": '{steps[].text == "Day" ? steps[].text : "Night"}',
        },
    )

    assert rows[0]["input"] == "Wake"
    assert rows[0]["expected_output"] == '["Day","Bake"]'
    assert rows[1]["input"] == "Rest"
    assert rows[1]["expected_output"] == "Night"


def test_map_records_supports_nested_array_comparisons_and_equals_alias() -> None:
    """Conditional expressions should match nested array values with ``=`` and order comparisons."""
    records = [
        {
            "logs": [
                {
                    "metadata": [
                        {"lot_id": 12},
                        {"lot_id": 8},
                    ]
                }
            ]
        },
        {
            "logs": [
                {
                    "metadata": [
                        {"lot_id": 5},
                    ]
                }
            ]
        },
    ]

    rows = map_records(
        records,
        {
            "input": '{logs[].metadata[].lot_id = 12 ? "Lot 12" : "Other lot"}',
            "expected_output": '{logs[].metadata[].lot_id > 10 ? "high" : "low"}',
        },
    )

    assert rows[0]["input"] == "Lot 12"
    assert rows[0]["expected_output"] == "high"
    assert rows[1]["input"] == "Other lot"
    assert rows[1]["expected_output"] == "low"


def test_list_field_candidates_uses_schema_style_paths() -> None:
    """Field candidates should describe the record schema, not sample row indices."""
    records = [
        {
            "name": "A",
            "ingredients": ["Flour", "Butter"],
            "steps": [{"text": "Mix"}, {"text": "Bake"}],
        },
        {
            "name": "B",
            "ingredients": ["Salt"],
            "steps": [{"text": "Serve"}],
        },
    ]

    candidates = list_field_candidates(records)

    assert "ingredients" in candidates
    assert "ingredients[]" in candidates
    assert "steps[].text" in candidates
    assert "steps[0].text" not in candidates
