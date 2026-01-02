"""
tinyagent.core.parsing
JSON parsing utilities for LLM responses.

Handles common LLM output wrappers like <think> tags and markdown code fences.
"""

from __future__ import annotations

import json
import re
from typing import Any


def parse_json_response(text: str) -> dict[str, Any] | None:
    """
    Parse JSON from LLM response, stripping common wrappers.

    Handles:
    - <think>...</think> reasoning blocks
    - Markdown code fences (```json ... ``` or ``` ... ```)

    Returns None if parsing fails.
    """
    cleaned = strip_llm_wrappers(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def strip_llm_wrappers(text: str) -> str:
    """Strip common LLM wrappers: <think> tags and markdown code fences."""
    # Remove <think>...</think> blocks (including empty ones)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    # Remove stray opening/closing think tags
    text = re.sub(r"</?think>", "", text)

    text = text.strip()

    # Extract from markdown code fence if present
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    return text
