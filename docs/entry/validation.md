---
title: Tool Validation
path: tinyagent/tools/validation.py
type: file
depth: 2
description: Static analysis validation for tool classes
exports:
  - validate_tool_class
  - ToolValidationError
seams: [E]
---

# Tool Validation

Static analysis system for validating tool classes to ensure they are safe, deterministic, and serializable.

## Overview

Tool validation uses Abstract Syntax Tree (AST) analysis to verify that tool classes meet structural requirements for safe use with LLMs.

## validate_tool_class

Main validation function for tool classes.

### Function Signature

```python
def validate_tool_class(tool_class: type) -> None:
    """
    Validate a tool class using AST analysis.

    Args:
        tool_class: Class to validate

    Raises:
        ToolValidationError: If validation fails
    """
```

### Usage Example

```python
from tinyagent import validate_tool_class

class MyTool:
    """A valid tool class."""

    def method(self, param: str) -> str:
        """Process parameter."""
        return param.upper()

# Validate the class
validate_tool_class(MyTool)  # Passes if valid
```

### Validation Rules

#### 1. Literal Default Values

Default values must be literals (not expressions or undefined names).

**Valid:**
```python
class GoodTool:
    def method(
        self,
        name: str = "default"  # Literal string
    ) -> str:
        return name
```

**Invalid:**
```python
class BadTool:
    DEFAULT_VALUE = "default"

    def method(
        self,
        name: str = DEFAULT_VALUE  # Non-literal reference
    ) -> str:
        return name
```

#### 2. Defined Names

All default value names must be defined within the class.

**Valid:**
```python
class GoodTool:
    LIMIT = 10

    def process(
        self,
        max_items: int = LIMIT  # Defined in class
    ) -> list:
        return []
```

**Invalid:**
```python
class BadTool:
    def process(
        self,
        max_items: int = UNDEFINED  # Not defined
    ) -> list:
        return []
```

#### 3. Simple Structure

Tool classes should be simple and avoid complex logic in defaults.

**Valid:**
```python
class GoodTool:
    def method(
        self,
        enabled: bool = True,
        count: int = 0,
        name: str = ""
    ) -> str:
        return name
```

**Invalid:**
```python
class BadTool:
    def method(
        self,
        config: dict = {}  # Mutable default
    ) -> dict:
        return config
```

## ToolValidationError

Exception raised when tool class validation fails.

### Definition

```python
class ToolValidationError(Exception):
    """Tool class validation failed."""
    pass
```

### Error Messages

```python
# Non-literal default
validate_tool_class(BadTool)
# ToolValidationError: Default value for 'param' must be a literal

# Undefined name
validate_tool_class(BadTool)
# ToolValidationError: Default value refers to undefined name 'UNDEFINED'

# Mutable default
validate_tool_class(BadTool)
# ToolValidationError: Default value for 'config' should not be mutable
```

### Handling Errors

```python
from tinyagent import validate_tool_class, ToolValidationError

try:
    validate_tool_class(MyTool)
    print("Tool class is valid")
except ToolValidationError as e:
    print(f"Validation failed: {e}")
    # Fix the issues and retry
```

## Implementation Details

### AST Analysis

Validation uses Python's `ast` module to analyze code structure:

```python
import ast

def validate_tool_class(tool_class: type) -> None:
    """Validate using AST analysis."""
    source = inspect.getsource(tool_class)
    tree = ast.parse(source)

    # Check all methods
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            validate_defaults(node)

    # Validate default values
    validate_default_values(tool_class)
```

### Default Value Extraction

Extract default values from function signatures:

```python
def get_default_values(func) -> dict:
    """Extract default values from function."""
    sig = inspect.signature(func)
    defaults = {}

    for name, param in sig.parameters.items():
        if param.default is not param.empty:
            defaults[name] = param.default

    return defaults
```

### Literal Checking

Check if values are literals:

```python
def is_literal(value) -> bool:
    """Check if value is a literal."""
    return isinstance(value, (
        str, int, float, bool,
        type(None), bytes,
        tuple, list, dict  # Only if all elements are literals
    ))
```

## Common Validation Failures

### 1. Non-Literal Defaults

```python
class BadTool:
    CONFIG = {"key": "value"}

    def method(
        self,
        config: dict = CONFIG  # Fails: not a literal
    ) -> dict:
        return config
```

**Fix:**
```python
class GoodTool:
    def method(
        self,
        config: dict = None  # Use None or literal
    ) -> dict:
        return config or {"key": "value"}
```

### 2. Undefined References

```python
class BadTool:
    def method(
        self,
        value: int = MAX_VALUE  # Fails: MAX_VALUE not defined
    ) -> int:
        return value
```

**Fix:**
```python
class GoodTool:
    MAX_VALUE = 100

    def method(
        self,
        value: int = MAX_VALUE  # Defined in class
    ) -> int:
        return value
```

### 3. Mutable Defaults

```python
class BadTool:
    def method(
        self,
        items: list = []  # Fails: mutable default
    ) -> list:
        return items
```

**Fix:**
```python
class GoodTool:
    def method(
        self,
        items: list = None  # Use None
    ) -> list:
        return items or []
```

### 4. Computed Defaults

```python
class BadTool:
    def method(
        self,
        value: int = calculate_default()  # Fails: function call
    ) -> int:
        return value
```

**Fix:**
```python
class GoodTool:
    DEFAULT_VALUE = 42  # Literal

    def method(
        self,
        value: int = DEFAULT_VALUE
    ) -> int:
        return value
```

## Integration with Tool System

### Validating Tool Classes

```python
from tinyagent import tool, validate_tool_class

class SearchTool:
    """Web search tool."""

    def search(
        self,
        query: str,
        max_results: int = 10  # Literal default
    ) -> str:
        """Search the web."""
        return f"Results for: {query}"

# Validate before use
validate_tool_class(SearchTool)

# Now safe to use
@tool
def search(query: str, max_results: int = 10) -> str:
    """Search the web."""
    return f"Results for: {query}"
```

### Automated Validation

```python
def create_tool(func):
    """Create tool with automatic validation."""
    # Validate function signature
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.default is not param.empty:
            if not is_literal(param.default):
                raise ToolDefinitionError(
                    f"Default for {param.name} must be literal"
                )

    # Create tool
    return tool(func)
```

## Testing Validation

### Unit Tests

```python
import pytest
from tinyagent import validate_tool_class, ToolValidationError

def test_literal_defaults():
    """Test that literal defaults pass validation."""
    class GoodTool:
        def method(self, value: str = "default") -> str:
            return value

    validate_tool_class(GoodTool)  # Should pass

def test_non_literal_defaults():
    """Test that non-literal defaults fail."""
    class BadTool:
        CONFIG = {"key": "value"}

        def method(self, config: dict = CONFIG) -> dict:
            return config

    with pytest.raises(ToolValidationError):
        validate_tool_class(BadTool)

def test_undefined_names():
    """Test that undefined names fail."""
    class BadTool:
        def method(self, value: int = UNDEFINED) -> int:
            return value

    with pytest.raises(ToolValidationError):
        validate_tool_class(BadTool)
```

### Integration Tests

```python
def test_tool_creation_with_validation():
    """Test tool creation with validation."""
    @tool
    def good_func(x: int = 0) -> int:
        return x

    # Should create tool successfully
    assert good_func.name == "good_func"

def test_tool_creation_fails_validation():
    """Test that validation fails for bad functions."""
    with pytest.raises(ToolDefinitionError):
        @tool
        def bad_func(x: int = UNDEFINED) -> int:  # type: ignore
            return x
```

## Best Practices

1. **Always use literal defaults**
   ```python
   def method(self, count: int = 0) -> int:  # Good
   ```

2. **Define constants in class**
   ```python
   class Tool:
       DEFAULT_LIMIT = 10

       def method(self, limit: int = DEFAULT_LIMIT) -> int:  # Good
           return limit
   ```

3. **Avoid mutable defaults**
   ```python
   def method(self, items: list = None) -> list:  # Good
       return items or []
   ```

4. **Validate before use**
   ```python
   validate_tool_class(MyTool)  # Validate early
   agent = ReactAgent(tools=[MyTool()])
   ```

5. **Handle validation errors**
   ```python
   try:
       validate_tool_class(MyTool)
   except ToolValidationError as e:
       print(f"Fix required: {e}")
   ```

## Security Considerations

### Why Validation Matters

1. **Serialization**: Tools must be serializable for API calls
2. **Determinism**: Non-literal defaults introduce uncertainty
3. **Safety**: Prevents code execution in default values
4. **Clarity**: Literal defaults are self-documenting

### Preventing Code Execution

```python
# Dangerous: Code in default value
class BadTool:
    def method(
        self,
        value: str = eval("42")  # Fails validation
    ) -> str:
        return value

# Safe: Literal value
class GoodTool:
    def method(
        self,
        value: str = "42"  # Literal
    ) -> str:
        return value
```

### Preventing Side Effects

```python
# Dangerous: Side effect in default
class BadTool:
    def method(
        self,
        value: list = open("data.txt").readlines()  # Fails
    ) -> list:
        return value

# Safe: No side effects
class GoodTool:
    def method(
        self,
        value: list = None
    ) -> list:
        if value is None:
            value = load_data()
        return value
```

## Advanced Usage

### Custom Validation Rules

```python
def custom_validator(tool_class: type) -> None:
    """Add custom validation rules."""
    # Check for specific patterns
    for name, method in inspect.getmembers(tool_class):
        if name.startswith("dangerous"):
            raise ToolValidationError(
                f"Method {name} not allowed"
            )

# Combine validators
def validate_tool(tool_class: type) -> None:
    """Run all validations."""
    validate_tool_class(tool_class)
    custom_validator(tool_class)
```

### Validation Decorator

```python
def validated_tool(func):
    """Decorator that validates before creating tool."""
    # Validate signature
    sig = inspect.signature(func)
    for param in sig.parameters.values():
        if param.default is not param.empty:
            if not is_literal(param.default):
                raise ToolDefinitionError(
                    f"Invalid default for {param.name}"
                )

    # Create tool
    return tool(func)

@validated_tool
def my_function(x: int = 0) -> int:
    return x
```

## Debugging Validation

### Inspect Validation Results

```python
from tinyagent import validate_tool_class
import ast

def debug_validation(tool_class: type):
    """Debug validation process."""
    source = inspect.getsource(tool_class)
    tree = ast.parse(source)

    print(f"Validating {tool_class.__name__}")
    print(f"Source:\n{source}")

    # Walk AST
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            print(f"Function: {node.name}")
            for arg in node.args.args:
                if arg.annotation:
                    print(f"  {arg.arg}: {ast.unparse(arg.annotation)}")

    # Validate
    try:
        validate_tool_class(tool_class)
        print("Validation passed")
    except ToolValidationError as e:
        print(f"Validation failed: {e}")

debug_validation(MyTool)
```

### Common Issues

**Issue:** Validation passes but tool fails at runtime
**Cause:** Validation checks AST, not runtime behavior
**Fix:** Add runtime tests for tool behavior

**Issue:** False positive validation failure
**Cause:** Overly strict validation rules
**Fix:** Modify validation or refactor code

**Issue:** Validation is slow
**Cause:** Parsing large tool classes
**Fix:** Cache validation results or validate once at import

## Future Enhancements

Planned improvements to validation system:
- Type hint validation
- Docstring validation
- Complexity analysis
- Security vulnerability scanning
- Performance impact analysis
- Dependency tracking
- Version compatibility checking
