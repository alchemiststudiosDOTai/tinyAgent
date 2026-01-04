---
title: Prompt Loader
path: prompts/loader.py
type: file
depth: 1
description: Dynamic prompt loading from files with fallback mechanism
exports: [load_prompt_from_file, get_prompt_fallback]
seams: [M]
---

# prompts/loader.py

## Where
`/Users/tuna/tinyAgent/tinyagent/prompts/loader.py`

## What
Provides utilities for dynamically loading prompt content from text files with fallback mechanism to default system prompt. Enables externalizing and customizing prompts without altering codebase.

## How

### Key Functions

**load_prompt_from_file(file_path: str) -> Optional[str]**
Reads prompt content from text file:
- **Supported Formats**: .txt, .md, .prompt, .xml
- **Validation**:
  - Checks file existence
  - Validates file type
  - Handles encoding issues
- **Error Handling**:
  - `FileNotFoundError`: File doesn't exist
  - `PermissionError`: No read access
  - `ValueError`: Invalid file type or encoding

**get_prompt_fallback(system_prompt: str, file_path: str | None = None) -> str**
Convenience function for robust prompt loading:
- Attempts to load from `file_path`
- Falls back to `system_prompt` if:
  - `file_path` is None
  - Loading fails
  - Loaded content is empty
- Logs warnings for loading failures
- Ensures agent always has valid prompt

**Usage Pattern:**
```python
# Try custom prompt, fall back to default
prompt = get_prompt_fallback(
    system_prompt=CODE_SYSTEM,
    file_path=user_provided_path
)
```

## Why

**Design Rationale:**
- **Flexibility**: Modify system prompts via file paths without code changes
- **Maintainability**: Separate prompt content from application logic
- **Robustness**: Fallback ensures agent always has instructions
- **Externalization**: Prompts as configuration, not code

**Architectural Role:**
- **Configurability**: Different agents/contexts use customized prompts
- **Adaptability**: Easy to swap prompts for different roles/tasks
- **A/B Testing**: Experiment with different prompt wordings
- **User Customization**: End-users can provide own instructions

**Dependencies:**
- `pathlib`: Path manipulation
- `logging`: Warning messages
- `typing`: Optional type hints
