"""Tests for PythonGraderComparer — user-defined Python grade() functions."""

import pytest

from src.comparers.python_grader import PythonGraderComparer


@pytest.mark.asyncio
async def test_basic_grade_function():
    """A simple grade function returning 1.0 should pass."""
    grader = PythonGraderComparer({
        "name": "basic",
        "source_code": "def grade(sample, item) -> float:\n    return 1.0\n",
        "threshold": 0.7,
    })

    score, passed, details = await grader.compare(
        expected="x", actual="y", row_data={"input": "q"},
    )

    assert score == 1.0
    assert passed is True
    assert details["grader_name"] == "basic"


@pytest.mark.asyncio
async def test_grade_uses_sample_and_item():
    """The grade function should have access to sample and item dicts."""
    source = (
        "def grade(sample, item) -> float:\n"
        "    if 'Paris' in sample['output_text'] and item.get('input') == 'capital':\n"
        "        return 1.0\n"
        "    return 0.0\n"
    )
    grader = PythonGraderComparer({
        "name": "context_check",
        "source_code": source,
        "threshold": 0.5,
    })

    score, passed, _ = await grader.compare(
        expected="Paris", actual="Paris is the capital", row_data={"input": "capital"},
    )
    assert score == 1.0
    assert passed is True


@pytest.mark.asyncio
async def test_score_clamped_above_one():
    """Scores above 1.0 should be clamped to 1.0."""
    grader = PythonGraderComparer({
        "name": "over",
        "source_code": "def grade(sample, item) -> float:\n    return 5.0\n",
        "threshold": 0.5,
    })

    score, passed, _ = await grader.compare(expected="", actual="", row_data={})
    assert score == 1.0


@pytest.mark.asyncio
async def test_score_clamped_below_zero():
    """Scores below 0.0 should be clamped to 0.0."""
    grader = PythonGraderComparer({
        "name": "under",
        "source_code": "def grade(sample, item) -> float:\n    return -2.0\n",
        "threshold": 0.5,
    })

    score, passed, _ = await grader.compare(expected="", actual="", row_data={})
    assert score == 0.0
    assert passed is False


@pytest.mark.asyncio
async def test_threshold_pass_fail():
    """Score exactly at threshold should pass; below should fail."""
    grader = PythonGraderComparer({
        "name": "thresh",
        "source_code": "def grade(sample, item) -> float:\n    return 0.7\n",
        "threshold": 0.7,
    })

    score, passed, _ = await grader.compare(expected="", actual="", row_data={})
    assert score == 0.7
    assert passed is True

    grader_strict = PythonGraderComparer({
        "name": "thresh_strict",
        "source_code": "def grade(sample, item) -> float:\n    return 0.69\n",
        "threshold": 0.7,
    })

    score, passed, _ = await grader_strict.compare(expected="", actual="", row_data={})
    assert score == 0.69
    assert passed is False


@pytest.mark.asyncio
async def test_syntax_error_returns_zero():
    """A syntax error in user code should score 0.0 with an error message."""
    grader = PythonGraderComparer({
        "name": "syntax_err",
        "source_code": "def grade(sample, item) -> float:\n    return !!!BAD\n",
        "threshold": 0.5,
    })

    score, passed, details = await grader.compare(expected="", actual="", row_data={})
    assert score == 0.0
    assert passed is False
    assert "error" in details


@pytest.mark.asyncio
async def test_runtime_error_returns_zero():
    """A runtime error in grade() should score 0.0 with an error message."""
    grader = PythonGraderComparer({
        "name": "runtime_err",
        "source_code": "def grade(sample, item) -> float:\n    return 1 / 0\n",
        "threshold": 0.5,
    })

    score, passed, details = await grader.compare(expected="", actual="", row_data={})
    assert score == 0.0
    assert passed is False
    assert "error" in details
    assert "division by zero" in details["error"]


@pytest.mark.asyncio
async def test_missing_grade_function():
    """Source code without a grade function should return an error."""
    grader = PythonGraderComparer({
        "name": "no_func",
        "source_code": "x = 42\n",
        "threshold": 0.5,
    })

    score, passed, details = await grader.compare(expected="", actual="", row_data={})
    assert score == 0.0
    assert passed is False
    assert "grade(sample, item)" in details["error"]


@pytest.mark.asyncio
async def test_restricted_import():
    """Importing disallowed modules should fail."""
    grader = PythonGraderComparer({
        "name": "import_blocked",
        "source_code": (
            "import os\n"
            "def grade(sample, item) -> float:\n"
            "    return 1.0\n"
        ),
        "threshold": 0.5,
    })

    score, passed, details = await grader.compare(expected="", actual="", row_data={})
    assert score == 0.0
    assert passed is False
    assert "error" in details


@pytest.mark.asyncio
async def test_allowed_import():
    """Importing allowed modules via import statement should work."""
    grader = PythonGraderComparer({
        "name": "import_allowed",
        "source_code": (
            "import re\n"
            "import json\n"
            "import math\n"
            "\n"
            "def grade(sample, item) -> float:\n"
            "    return 1.0 if math.sqrt(4) == 2.0 else 0.0\n"
        ),
        "threshold": 0.5,
    })

    score, passed, _ = await grader.compare(expected="", actual="", row_data={})
    assert score == 1.0
    assert passed is True


@pytest.mark.asyncio
async def test_restricted_open():
    """open() should not be available in user code."""
    grader = PythonGraderComparer({
        "name": "open_blocked",
        "source_code": (
            "def grade(sample, item) -> float:\n"
            "    f = open('/etc/passwd')\n"
            "    return 1.0\n"
        ),
        "threshold": 0.5,
    })

    score, passed, details = await grader.compare(expected="", actual="", row_data={})
    assert score == 0.0
    assert passed is False
    assert "error" in details


@pytest.mark.asyncio
async def test_allowed_modules_available():
    """re, json, and math should be available as pre-imported globals."""
    grader = PythonGraderComparer({
        "name": "modules",
        "source_code": (
            "def grade(sample, item) -> float:\n"
            "    return 1.0 if math.sqrt(4) == 2.0 else 0.0\n"
        ),
        "threshold": 0.5,
    })

    score, passed, _ = await grader.compare(expected="", actual="", row_data={})
    assert score == 1.0
    assert passed is True


@pytest.mark.asyncio
async def test_re_module_usable():
    """User code should be able to use re for pattern matching."""
    source = (
        "def grade(sample, item) -> float:\n"
        "    if re.search(re.escape(item['keyword']), sample['output_text']):\n"
        "        return 1.0\n"
        "    return 0.0\n"
    )
    grader = PythonGraderComparer({
        "name": "re_check",
        "source_code": source,
        "threshold": 0.5,
    })

    score, passed, _ = await grader.compare(
        expected="", actual="Hello World", row_data={"keyword": "World"},
    )
    assert score == 1.0


@pytest.mark.asyncio
async def test_no_row_data():
    """When row_data is None, item should be an empty dict."""
    grader = PythonGraderComparer({
        "name": "no_row",
        "source_code": (
            "def grade(sample, item) -> float:\n"
            "    return 1.0 if isinstance(item, dict) else 0.0\n"
        ),
        "threshold": 0.5,
    })

    score, passed, _ = await grader.compare(expected="", actual="hi", row_data=None)
    assert score == 1.0
    assert passed is True
