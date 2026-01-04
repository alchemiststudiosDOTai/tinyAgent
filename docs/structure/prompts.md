---
title: Prompts
path: prompts/
type: directory
depth: 0
description: Prompt template management and loading for agent system prompts
seams: [PromptLoader, SystemPrompt]
---

## Directory Purpose and Organization

The `prompts` directory is responsible for managing and providing prompt templates used by the `tinyagent` system. It's organized into modules for loading prompts from files and defining static prompt templates.

## Naming Conventions

- **Files**: Descriptive `snake_case` (e.g., `loader.py`, `templates.py`)
- **Functions**: `snake_case` (e.g., `load_prompt_from_file`, `get_prompt_fallback`)
- **Constants/Global Variables**: `UPPER_SNAKE_CASE` for prompt template strings (e.g., `SYSTEM`, `BAD_JSON`, `CODE_SYSTEM`)
- **Variables**: `snake_case`

## Relationship to Sibling Directories

The `prompts` directory serves as a core component for defining agent behavior and interaction styles. Other directories import and utilize these prompt templates:

- **`agents`**: Particularly `agents/code.py` and `agents/react.py` import and use these prompt templates to guide agent operations and responses
- **`core`**: For overall system configuration and prompt consumption
- **`execution`**: For environments that execute code with prompts

## File Structure and Architecture

### `__init__.py`

Acts as the package's entry point, controlling what symbols are directly accessible when `tinyagent.prompts` is imported:

- `SYSTEM`: General tool-using assistant system prompt
- `BAD_JSON`: Error handling prompt for JSON formatting issues
- `CODE_SYSTEM`: Python code execution agent system prompt
- `get_prompt_fallback`: Utility function for loading prompts with fallback

### `loader.py`

Provides utility functions for dynamically loading prompt content:

- **`load_prompt_from_file`**: Loads prompt content from specified files (e.g., `.txt`, `.md`, `.prompt`, `.xml`)
  - Includes error handling for file operations
  - Raises `FileNotFoundError` if file doesn't exist
  - Raises `IOError` for read failures

- **`get_prompt_fallback`**: Provides a fallback mechanism to a default prompt if loading fails
  - Returns file content if successful
  - Falls back to provided default string if file operations fail

### `templates.py`

Contains predefined, static string templates that serve as foundational prompts for different agent roles or scenarios:

- **`SYSTEM`**: General tool-using assistant prompt
  - Defines the agent's role
  - Outlines critical rules
  - Specifies response format requirements
  - Provides examples

- **`BAD_JSON`**: Error recovery prompt
  - Handles JSON formatting errors
  - Guides the LLM to correct malformed responses

- **`CODE_SYSTEM`**: Python code execution agent prompt
  - Defines the code execution environment
  - Specifies security constraints
  - Outlines available Python capabilities
  - Provides code execution examples

## Architecture Summary

The `prompts` directory provides a flexible, file-based prompt management system with fallback capabilities. This design allows for:

1. Easy customization of agent behavior through external prompt files
2. Graceful degradation to default prompts when files are unavailable
3. Clear separation between prompt content and agent logic
4. Multiple prompt types for different agent implementations
