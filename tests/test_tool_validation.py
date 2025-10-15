import os
import time

import pytest

from tinyagent.tools.validation import ToolValidationError, validate_tool_class

TOKEN = "abc123"


def make_client():
    """Dummy function for testing undefined name detection."""
    return None


class ValidTool:
    """A compliant tool implementation used for validation."""

    name = "valid"
    description = "Well-behaved tool"
    headers = {"Authorization": "Bearer"}

    def __init__(self, base_url: str = "https://example.com", retries: int = 3) -> None:
        self.base_url = base_url
        self.retries = retries

    def run(self) -> str:
        return f"{self.base_url}:{self.retries}"


class BrokenTool:
    """Intentionally violates validator rules."""

    settings = os.environ

    def __init__(self, api_key: str, timestamp: float = time.time()) -> None:  # type: ignore[misc]
        self.api_key = api_key
        self.token = TOKEN
        self.client = make_client()  # noqa: F821


def test_validate_tool_class_finds_violations():
    validate_tool_class(ValidTool)

    with pytest.raises(ToolValidationError) as exc:
        validate_tool_class(BrokenTool)

    message = str(exc.value)
    assert "Class attribute values must be literals" in message
    assert "__init__ parameters must all provide default literal values" in message
    assert "Undefined name 'make_client'" in message
