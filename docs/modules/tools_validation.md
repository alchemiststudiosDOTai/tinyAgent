---
title: Tool Validation
path: tools/validation.py
type: file
depth: 1
description: Static analysis validation for tool class structure and serialization safety
exports: [validate_tool_class, ToolValidationError]
seams: [M]
---

# tools/validation.py

## Where
`/Users/tuna/tinyAgent/tinyagent/tools/validation.py`

## What
Performs static analysis on Python tool classes using AST module. Ensures tool implementations remain simple, deterministic, and easily serializable for reliable agent usage.

## How

### Key Classes

**ToolValidationError**
Raised when tool class fails validation checks

### Key Functions

**validate_tool_class(cls: type) -> None**
Public entry point for validation:
- Extracts source code from class
- Parses into Abstract Syntax Tree (AST)
- Applies series of validation rules
- Raises `ToolValidationError` with detailed messages on failure

**Validation Rules:**

**_validate_init_signature / _check_init**
- `self` must be first parameter
- No positional-only parameters
- No `*args` or `**kwargs`
- All parameters must have literal default values

**_validate_class_body**
- Only allows: docstrings, method definitions, literal attribute assignments

**_validate_methods**
- Applies `_function_analyzer` to each method
- Checks for undefined name references
- Prohibits `global` and `nonlocal` declarations
- Disallows `lambda` expressions

**_is_literal**
- Recursively checks if AST node represents literal value
- Supports numbers, strings, booleans, lists, tuples, dicts

**Helper Functions:**
- `_collect_module_names`: Builds symbol table from module AST
- `_find_class_node`: Locates ClassDef node for tool class
- `_function_analyzer`: AST visitor for method body validation

## Why

**Design Rationale:**
- **Serialization Friendliness**: Literal defaults enable easy JSON/config serialization
- **Determinism**: Restricting dynamic features ensures predictable behavior
- **Static Enforceability**: AST analysis catches issues before runtime
- **Clarity**: Simple tools easier to understand and maintain

**Architectural Role:**
- **Gatekeeper**: Ensures tools conform to agent requirements
- **Registration**: Applied during tool loading/registration
- **Reliability**: Guarantees stable, predictable tool behavior
- **Agent Integration**: Ensures tools can be reliably understood and used

**Dependencies:**
- `ast`: Abstract Syntax Tree parsing and analysis
- `inspect`: Source code extraction
- `typing`: Type hints
- `dataclasses`: Function analyzer structure

## Verification

The validation logic is rigorously tested with negative boundary cases to ensure that it correctly identifies and rejects invalid tool definitions. These tests are located in `tests/test_validation.py`.

**Tested Violations:**
- **Initialization**: Missing `self` parameter, non-literal default values.
- **Attributes**: Class attributes with non-literal values.
- **Methods**: Usage of `global` or `nonlocal` declarations, `lambda` expressions, and references to undefined names.

To run the validation tests:

```bash
pytest tests/test_validation.py
```
