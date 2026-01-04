import pytest

from tinyagent.tools.validation import ToolValidationError, validate_tool_class


# --- Valid Tool ---
class GoodTool:
    """A valid tool example."""

    timeout = 10

    def __init__(self, api_key: str = "default_key"):
        self.api_key = api_key

    def run(self, query: str) -> str:
        return query.upper()


# --- Invalid Tools ---


class BadInitNoSelf:
    def __init__(x, y):  # Missing self
        pass


class BadInitNonLiteralDefault:
    def __init__(self, x=set()):  # set() is not a literal in AST usually
        pass


def _make_default():
    return "dynamic"


class BadInitDynamicDefault:
    def __init__(self, x=_make_default()):
        pass


class BadClassAttribute:
    config = [x for x in range(10)]  # List comprehension is not a literal


global_var = 10


class BadMethodExplicitGlobal:
    def run(self):
        global global_var
        return global_var


class BadMethodUndefined:
    def run(self):
        return undefined_var  # noqa: F821


class BadMethodLambda:
    def run(self):
        f = lambda x: x + 1  # noqa: E731

        return f(10)


def test_validation_good_tool():
    """Ensure a compliant tool passes validation."""
    validate_tool_class(GoodTool)


def test_validation_bad_init_no_self():
    with pytest.raises(ToolValidationError, match="must declare 'self'"):
        validate_tool_class(BadInitNoSelf)


def test_validation_bad_init_dynamic_default():
    with pytest.raises(ToolValidationError, match="must be a literal"):
        validate_tool_class(BadInitDynamicDefault)


def test_validation_bad_class_attribute():
    with pytest.raises(ToolValidationError, match="must be literals"):
        validate_tool_class(BadClassAttribute)


def test_validation_bad_method_explicit_global():
    with pytest.raises(ToolValidationError, match="Global declarations are not allowed"):
        validate_tool_class(BadMethodExplicitGlobal)


def test_validation_bad_method_undefined():
    with pytest.raises(ToolValidationError, match="Undefined name 'undefined_var'"):
        validate_tool_class(BadMethodUndefined)


def test_validation_bad_method_lambda():
    with pytest.raises(ToolValidationError, match="Lambdas are not allowed"):
        validate_tool_class(BadMethodLambda)
