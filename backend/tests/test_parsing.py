"""Tests for robust JSON extraction from LLM outputs."""

import pytest

from app.recommendations.parsing import extract_first_json_object


class TestExtractFirstJsonObject:
    def test_plain_json(self) -> None:
        result = extract_first_json_object('{"key": "value", "num": 42}')
        assert result == {"key": "value", "num": 42}

    def test_with_markdown_fence(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        assert extract_first_json_object(text) == {"key": "value"}

    def test_with_markdown_fence_no_language(self) -> None:
        text = '```\n{"key": "value"}\n```'
        assert extract_first_json_object(text) == {"key": "value"}

    def test_with_preamble(self) -> None:
        text = 'Here is the response: {"answer": "yes"}'
        assert extract_first_json_object(text) == {"answer": "yes"}

    def test_with_postamble(self) -> None:
        text = '{"answer": "yes"} Hope this helps!'
        assert extract_first_json_object(text) == {"answer": "yes"}

    def test_nested_objects(self) -> None:
        text = '{"outer": {"inner": {"deep": "value"}}}'
        result = extract_first_json_object(text)
        assert result == {"outer": {"inner": {"deep": "value"}}}

    def test_with_arrays(self) -> None:
        text = '{"items": [1, 2, {"nested": true}]}'
        assert extract_first_json_object(text) == {"items": [1, 2, {"nested": True}]}

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="Empty response"):
            extract_first_json_object("")

    def test_no_json_raises(self) -> None:
        with pytest.raises(ValueError, match="No JSON object found"):
            extract_first_json_object("Just plain text with no JSON")

    def test_malformed_json_raises(self) -> None:
        with pytest.raises(ValueError, match="Malformed JSON"):
            extract_first_json_object('{"key": "value"')  # missing closing brace

    def test_array_at_top_level_raises(self) -> None:
        with pytest.raises(ValueError, match="No JSON object found"):
            extract_first_json_object("[1, 2, 3]")

    def test_string_with_braces_inside_handled(self) -> None:
        text = '{"description": "use {placeholder} syntax"}'
        result = extract_first_json_object(text)
        assert result == {"description": "use {placeholder} syntax"}
