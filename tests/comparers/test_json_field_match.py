"""Tests for json_field_match comparer."""

import pytest

from src.comparers.json_field_match import JsonFieldMatchComparer, _find_field


class TestFindField:
    """Tests for the recursive _find_field helper."""

    def test_top_level_field(self) -> None:
        obj = {"answer": "Paris", "confidence": 95}
        found, value = _find_field(obj, "answer")
        assert found is True
        assert value == "Paris"

    def test_nested_field(self) -> None:
        obj = {"result": {"data": {"answer": "Tokyo"}}}
        found, value = _find_field(obj, "answer")
        assert found is True
        assert value == "Tokyo"

    def test_field_in_list_of_dicts(self) -> None:
        obj = {"results": [{"id": 1}, {"id": 2, "answer": "Berlin"}]}
        found, value = _find_field(obj, "answer")
        assert found is True
        assert value == "Berlin"

    def test_returns_first_match(self) -> None:
        obj = {"answer": "first", "nested": {"answer": "second"}}
        found, value = _find_field(obj, "answer")
        assert found is True
        assert value == "first"

    def test_field_not_found(self) -> None:
        obj = {"foo": "bar", "nested": {"baz": 42}}
        found, value = _find_field(obj, "answer")
        assert found is False
        assert value is None

    def test_empty_dict(self) -> None:
        found, value = _find_field({}, "answer")
        assert found is False
        assert value is None

    def test_plain_list(self) -> None:
        obj = [{"a": 1}, {"answer": "found"}]
        found, value = _find_field(obj, "answer")
        assert found is True
        assert value == "found"

    def test_scalar_input(self) -> None:
        found, value = _find_field("just a string", "answer")
        assert found is False
        assert value is None


class TestJsonFieldMatchComparer:
    """Tests for the JsonFieldMatchComparer."""

    @pytest.mark.asyncio
    async def test_exact_match_top_level(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "answer"})
        score, passed, details = await comparer.compare(
            expected="Paris",
            actual='{"answer": "Paris", "confidence": 95}',
        )
        assert score == 1.0
        assert passed is True
        assert details["extracted_value"] == "Paris"

    @pytest.mark.asyncio
    async def test_match_nested_field(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "answer"})
        score, passed, details = await comparer.compare(
            expected="Tokyo",
            actual='{"result": {"reasoning": "...", "answer": "Tokyo"}}',
        )
        assert score == 1.0
        assert passed is True

    @pytest.mark.asyncio
    async def test_match_deeply_nested(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "value"})
        score, passed, details = await comparer.compare(
            expected="42",
            actual='{"level1": {"level2": {"level3": {"value": 42}}}}',
        )
        assert score == 1.0
        assert passed is True

    @pytest.mark.asyncio
    async def test_mismatch(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "answer"})
        score, passed, details = await comparer.compare(
            expected="London",
            actual='{"answer": "Paris"}',
        )
        assert score == 0.0
        assert passed is False

    @pytest.mark.asyncio
    async def test_case_insensitive_default(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "answer"})
        score, passed, _ = await comparer.compare(
            expected="paris",
            actual='{"answer": "PARIS"}',
        )
        assert score == 1.0
        assert passed is True

    @pytest.mark.asyncio
    async def test_case_sensitive(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "answer", "case_sensitive": True})
        score, passed, _ = await comparer.compare(
            expected="paris",
            actual='{"answer": "PARIS"}',
        )
        assert score == 0.0
        assert passed is False

    @pytest.mark.asyncio
    async def test_strip_whitespace(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "answer"})
        score, passed, _ = await comparer.compare(
            expected="  Paris  ",
            actual='{"answer": " Paris "}',
        )
        assert score == 1.0
        assert passed is True

    @pytest.mark.asyncio
    async def test_invalid_json(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "answer"})
        score, passed, details = await comparer.compare(
            expected="Paris",
            actual="not json at all",
        )
        assert score == 0.0
        assert passed is False
        assert "error" in details

    @pytest.mark.asyncio
    async def test_field_not_found(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "answer"})
        score, passed, details = await comparer.compare(
            expected="Paris",
            actual='{"question": "What is the capital?"}',
        )
        assert score == 0.0
        assert passed is False
        assert "not found" in details["error"]

    @pytest.mark.asyncio
    async def test_default_field_name_is_key(self) -> None:
        comparer = JsonFieldMatchComparer({})
        score, passed, details = await comparer.compare(
            expected="some_value",
            actual='{"key": "some_value"}',
        )
        assert score == 1.0
        assert passed is True
        assert details["field_name"] == "key"

    @pytest.mark.asyncio
    async def test_field_in_array(self) -> None:
        comparer = JsonFieldMatchComparer({"field_name": "label"})
        score, passed, _ = await comparer.compare(
            expected="urgent",
            actual='{"items": [{"id": 1}, {"id": 2, "label": "urgent"}]}',
        )
        assert score == 1.0
        assert passed is True
