"""Tests for template_utils — Jinja-style placeholder rendering."""

import pytest

from src.comparers.template_utils import render_template


class TestRenderTemplate:
    """Test the render_template helper."""

    def test_simple_variable(self):
        result = render_template("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

    def test_nested_dict_access(self):
        ctx = {"item": {"input": "What is Python?", "category": "tech"}}
        result = render_template("Q: {{ item.input }}", ctx)
        assert result == "Q: What is Python?"

    def test_sample_output_text(self):
        ctx = {"sample": {"output_text": "Paris is the capital"}}
        result = render_template("Output: {{ sample.output_text }}", ctx)
        assert result == "Output: Paris is the capital"

    def test_multiple_placeholders(self):
        ctx = {"item": {"input": "Q1"}, "sample": {"output_text": "A1"}}
        result = render_template("{{ item.input }} -> {{ sample.output_text }}", ctx)
        assert result == "Q1 -> A1"

    def test_unresolvable_placeholder_left_as_is(self):
        result = render_template("{{ item.missing }}", {"item": {"other": "val"}})
        assert result == "{{ item.missing }}"

    def test_missing_top_level_key(self):
        result = render_template("{{ unknown.field }}", {})
        assert result == "{{ unknown.field }}"

    def test_no_placeholders(self):
        result = render_template("plain text", {"item": {}})
        assert result == "plain text"

    def test_whitespace_in_braces(self):
        result = render_template("{{  item.x  }}", {"item": {"x": "42"}})
        assert result == "42"

    def test_numeric_value_converted_to_string(self):
        result = render_template("{{ item.count }}", {"item": {"count": 7}})
        assert result == "7"

    def test_empty_template(self):
        result = render_template("", {"item": {"x": "y"}})
        assert result == ""
