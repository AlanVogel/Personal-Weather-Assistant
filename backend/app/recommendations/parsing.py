"""Robust JSON extraction from LLM responses."""

import json
from typing import Any


def extract_first_json_object(text: str) -> dict[str, Any]:
    r"""Extract the first valid JSON object from raw LLM output.

    Uses ``json.JSONDecoder.raw_decode`` to walk the text character by character,
    which is more robust than regex matching (it handles nested braces and braces
    inside strings). Handles common LLM output shapes:

    - Plain JSON: `{"key": "value"}`
    - Markdown-fenced: ` ```json\n{...}\n``` `
    - JSON with preamble: `Here is the answer: {...}`
    - JSON with postamble: `{...} Hope this helps!`

    Args:
        text: Raw text returned by the model.

    Returns:
        The first decoded JSON object as a dict.

    Raises:
        ValueError: No valid JSON object is found in the text.
    """
    if not text:
        raise ValueError("Empty response")

    # Strip common markdown fences first
    cleaned = _strip_markdown_fences(text)

    # Find first '{' and try to decode from there
    decoder = json.JSONDecoder()
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    try:
        obj, _ = decoder.raw_decode(cleaned[start:])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in response: {exc.msg}") from exc

    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object, got {type(obj).__name__}")

    return obj


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) if present."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Skip opening fence line
        lines = stripped.split("\n")
        if len(lines) >= 2:
            # Remove first line (```json or ```) and find closing fence
            content_lines = lines[1:]
            for i, line in enumerate(content_lines):
                if line.strip().startswith("```"):
                    return "\n".join(content_lines[:i])
            return "\n".join(content_lines)
    return stripped
