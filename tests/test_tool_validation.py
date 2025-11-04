import pytest

from tinyagent.tools.validation import ToolValidationError, validate_tool_class

# Module-level variable used to demonstrate non-literal class attribute
bad_variable = "this is not a literal in the class definition"


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

    name = bad_variable  # ✗ Missing quotes (not a literal)
    description = "Well-behaved tool"
    headers = {"Authorization": "Bearer"}

    def __init__(self, base_url: str, retries: int = 3) -> None:  # ✗ base_url missing default
        self.base_url = base_url
        self.retries = retries
        self.client = None  # ✗ No type annotation

    def run(self) -> str:
        return f"{self.base_url}:{self.retries}"


def test_validate_tool_class_finds_violations():
    validate_tool_class(ValidTool)

    print("\n=== BrokenTool violations ===")
    print("Line 27: name = bad_variable")
    print("  → 'bad_variable' is a variable reference, NOT a string literal")
    print("  → Compare to ValidTool line 12: name = 'valid' ✓")
    print("  → Triggers validation.py:154-157")

    print("\nLine 31: def __init__(self, base_url: str, retries: int = 3):")
    print("  → 'base_url' parameter has NO default value")
    print("  → Compare to ValidTool line 16: all params have defaults ✓")
    print("  → Validator requires ALL params (except self) have literal defaults")
    print("  → Triggers validation.py:184-191")

    print("\nLine 34: self.client = None")
    print("  → Assignment to None WITHOUT type annotation")
    print("  → Should be: self.client: SomeType | None = None")
    print("  → ValidTool doesn't assign None (lines 17-18) ✓")
    print("  → Triggers validation.py:293-301")

    with pytest.raises(ToolValidationError) as exc:
        validate_tool_class(BrokenTool)

    message = str(exc.value)
    print(f"\n=== Error message ===\n{message}")

    assert "Class attribute values must be literals" in message
    assert "__init__ parameters must all provide default literal values" in message
    assert "Assignment to None requires type annotation" in message
