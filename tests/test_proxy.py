"""Tests for proxy serialization boundaries."""

from __future__ import annotations

from typing import Any

import pytest

from tinyagent.agent_types import Context, TextContent, UserMessage
from tinyagent.proxy import _context_to_json, _message_to_json


def test_message_to_json_rejects_value_without_model_dump() -> None:
    with pytest.raises(TypeError, match="context.messages"):
        _message_to_json(object())


def test_message_to_json_rejects_model_dump_returning_non_dict() -> None:
    class BadDump:
        def model_dump(self, *, exclude_none: bool = True) -> list[object]:
            del exclude_none
            return []

    with pytest.raises(TypeError, match="must return a dict"):
        _message_to_json(BadDump())


def test_context_to_json_requires_model_messages() -> None:
    bad_messages: list[Any] = [object()]
    context = Context(
        system_prompt="test",
        messages=bad_messages,
    )
    with pytest.raises(TypeError, match="context.messages"):
        _context_to_json(context)


def test_context_to_json_accepts_model_messages() -> None:
    context = Context(
        system_prompt="test",
        messages=[UserMessage(content=[TextContent(text="hello")])],
    )
    payload = _context_to_json(context)
    assert payload["system_prompt"] == "test"
    assert isinstance(payload["messages"], list)
