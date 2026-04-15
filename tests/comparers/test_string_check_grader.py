"""Tests for StringCheckGraderComparer — deterministic string comparison grader."""

import pytest

from src.comparers.string_check_grader import StringCheckGraderComparer


@pytest.mark.asyncio
async def test_equals_match():
    """Exact string equality should score 1.0."""
    grader = StringCheckGraderComparer({
        "name": "eq_check",
        "input_value": "{{ sample.output_text }}",
        "operation": "equals",
        "reference_value": "{{ item.expected_output }}",
        "threshold": 1.0,
    })

    score, passed, details = await grader.compare(
        expected="Paris",
        actual="Paris",
        row_data={"expected_output": "Paris"},
    )

    assert score == 1.0
    assert passed is True
    assert details["operation"] == "equals"


@pytest.mark.asyncio
async def test_equals_mismatch():
    """Non-matching strings should score 0.0."""
    grader = StringCheckGraderComparer({
        "name": "eq_check",
        "input_value": "{{ sample.output_text }}",
        "operation": "equals",
        "reference_value": "{{ item.expected_output }}",
        "threshold": 1.0,
    })

    score, passed, details = await grader.compare(
        expected="Paris",
        actual="London",
        row_data={"expected_output": "Paris"},
    )

    assert score == 0.0
    assert passed is False


@pytest.mark.asyncio
async def test_not_equals():
    """not_equals should pass when values differ."""
    grader = StringCheckGraderComparer({
        "name": "neq",
        "input_value": "{{ sample.output_text }}",
        "operation": "not_equals",
        "reference_value": "{{ item.bad_answer }}",
        "threshold": 1.0,
    })

    score, passed, _ = await grader.compare(
        expected="",
        actual="Paris",
        row_data={"bad_answer": "London"},
    )

    assert score == 1.0
    assert passed is True


@pytest.mark.asyncio
async def test_not_equals_fail():
    """not_equals should fail when values are the same."""
    grader = StringCheckGraderComparer({
        "name": "neq",
        "input_value": "{{ sample.output_text }}",
        "operation": "not_equals",
        "reference_value": "{{ item.val }}",
        "threshold": 1.0,
    })

    score, passed, _ = await grader.compare(
        expected="",
        actual="same",
        row_data={"val": "same"},
    )

    assert score == 0.0
    assert passed is False


@pytest.mark.asyncio
async def test_contains():
    """contains should pass when reference is a substring of input."""
    grader = StringCheckGraderComparer({
        "name": "contains_check",
        "input_value": "{{ sample.output_text }}",
        "operation": "contains",
        "reference_value": "{{ item.keyword }}",
        "threshold": 1.0,
    })

    score, passed, _ = await grader.compare(
        expected="",
        actual="The capital of France is Paris.",
        row_data={"keyword": "Paris"},
    )

    assert score == 1.0
    assert passed is True


@pytest.mark.asyncio
async def test_contains_fail():
    """contains should fail when reference is NOT a substring."""
    grader = StringCheckGraderComparer({
        "name": "contains_check",
        "input_value": "{{ sample.output_text }}",
        "operation": "contains",
        "reference_value": "{{ item.keyword }}",
        "threshold": 1.0,
    })

    score, passed, _ = await grader.compare(
        expected="",
        actual="The capital of France is Paris.",
        row_data={"keyword": "Berlin"},
    )

    assert score == 0.0
    assert passed is False


@pytest.mark.asyncio
async def test_contains_ignore_case():
    """contains_ignore_case should match regardless of case."""
    grader = StringCheckGraderComparer({
        "name": "ci_check",
        "input_value": "{{ sample.output_text }}",
        "operation": "contains_ignore_case",
        "reference_value": "{{ item.keyword }}",
        "threshold": 1.0,
    })

    score, passed, _ = await grader.compare(
        expected="",
        actual="HELLO WORLD",
        row_data={"keyword": "hello"},
    )

    assert score == 1.0
    assert passed is True


@pytest.mark.asyncio
async def test_threshold_pass_fail():
    """A binary 0.0 score should fail with threshold 0.7 but a 1.0 score should pass."""
    grader = StringCheckGraderComparer({
        "name": "threshold_test",
        "input_value": "{{ sample.output_text }}",
        "operation": "equals",
        "reference_value": "{{ item.ref }}",
        "threshold": 0.7,
    })

    # Match → score 1.0, threshold 0.7 → passed
    score, passed, _ = await grader.compare(
        expected="", actual="hello", row_data={"ref": "hello"},
    )
    assert passed is True

    # Mismatch → score 0.0, threshold 0.7 → failed
    score, passed, _ = await grader.compare(
        expected="", actual="hello", row_data={"ref": "world"},
    )
    assert passed is False


@pytest.mark.asyncio
async def test_missing_row_data():
    """When row_data is None, template placeholders for item stay unresolved."""
    grader = StringCheckGraderComparer({
        "name": "no_row",
        "input_value": "{{ sample.output_text }}",
        "operation": "equals",
        "reference_value": "{{ item.ref }}",
        "threshold": 1.0,
    })

    score, passed, details = await grader.compare(
        expected="hello", actual="hello", row_data=None,
    )

    # item.ref cannot resolve → stays as template → doesn't match "hello"
    assert score == 0.0
    assert passed is False
    assert details["resolved_reference"] == "{{ item.ref }}"


@pytest.mark.asyncio
async def test_unknown_operation():
    """An invalid operation should return 0.0 and include error."""
    grader = StringCheckGraderComparer({
        "name": "bad_op",
        "input_value": "a",
        "operation": "starts_with",
        "reference_value": "a",
        "threshold": 1.0,
    })

    score, passed, details = await grader.compare(
        expected="", actual="hello", row_data={},
    )

    assert score == 0.0
    assert passed is False
    assert "error" in details


@pytest.mark.asyncio
async def test_details_contain_resolved_values():
    """Details should include the resolved input and reference strings."""
    grader = StringCheckGraderComparer({
        "name": "detail_check",
        "input_value": "{{ sample.output_text }}",
        "operation": "equals",
        "reference_value": "{{ item.answer }}",
        "threshold": 1.0,
    })

    _, _, details = await grader.compare(
        expected="", actual="42", row_data={"answer": "42"},
    )

    assert details["resolved_input"] == "42"
    assert details["resolved_reference"] == "42"
    assert details["grader_name"] == "detail_check"
