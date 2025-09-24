# Research – Prompt Handling System Analysis
**Date:** 2025-09-23
**Owner:** Claude Code
**Phase:** Research

## Goal
Analyze the current prompt handling system in tinyagent to understand how users can pass prompts to the AI agent and identify improvements needed for cleaner prompt passing.

## Additional Search
- `grep -ri "prompt" .claude/` - No matches in .claude directory
- `grep -ri "system" .claude/` - No matches in .claude directory

## Findings

### Relevant files & why they matter:
- **`/home/fabian/tinyAgent/tinyagent/prompt.py`** → Contains all hardcoded system prompt templates (SYSTEM, BAD_JSON, CODE_SYSTEM) - the central prompt repository
- **`/home/fabian/tinyAgent/tinyagent/agents/agent.py`** → ReactAgent implementation showing how prompts are initialized and used in the ReAct loop
- **`/home/fabian/tinyAgent/tinyagent/agents/code_agent.py`** → TinyCodeAgent implementation with limited prompt customization via system_suffix parameter
- **`/home/fabian/tinyAgent/examples/simple_demo.py`** → Shows current usage pattern with no prompt customization
- **`/home/fabian/tinyAgent/examples/react_demo.py`** → Enhanced example using default prompts only
- **`/home/fabian/tinyAgent/examples/code_demo.py`** → Code agent example with system_suffix as the only customization option
- **`/home/fabian/tinyAgent/tests/api_test/test_agent.py`** → Test coverage for prompt generation and immutability

## Key Patterns / Solutions Found

### Current Implementation Architecture
- **Centralized prompt storage**: All prompts in single `prompt.py` file
- **Immutable prompt construction**: Prompts built once during `__post_init__` and never modified
- **Template-based approach**: Uses Python string formatting with `{tools}` and `{helpers}` variables
- **Hardcoded system prompts**: Users must modify source code for any prompt changes

### Existing Customization Mechanisms
- **TinyCodeAgent.system_suffix**: Only allows appending text to base prompt (limited customization)
- **No prompt parameters**: Agent constructors don't accept prompt customization
- **No file loading**: No mechanisms exist for loading prompts from external files
- **No environment variables**: No support for prompt configuration via environment

### Available Infrastructure for Extension
- **PyYAML dependency**: Already available for YAML prompt file support
- **File I/O patterns**: Documentation shows proper file reading with error handling
- **Configuration management**: Environment variable patterns already established
- **Tool registry system**: Could be extended for prompt loading tools
- **JSON parsing**: Already used in agent for payload handling

### Current Usage Patterns
```python
# ReactAgent - no prompt customization
agent = ReactAgent(tools=[tool1, tool2])

# TinyCodeAgent - limited customization via suffix
agent = TinyCodeAgent(tools=[tool1, tool2], system_suffix="Additional instructions")
```

## Knowledge Gaps

### Missing Context for Implementation
- **No existing prompt file format standards**: Need to define XML/YAML/JSON prompt file structure
- **No prompt validation system**: Need to establish prompt format validation rules
- **No prompt versioning strategy**: Need to consider how to handle prompt version management
- **No prompt caching mechanisms**: Need to determine if prompt files should be cached or reloaded
- **No prompt composition patterns**: Need to define how multiple prompt sources should be combined

### User Experience Considerations
- **Backward compatibility requirements**: Must maintain existing default behavior
- **Error handling strategy**: Need to define how to handle missing or invalid prompt files
- **Performance implications**: File loading vs. hardcoded prompt performance trade-offs
- **Security considerations**: Need to validate prompt file sources and content

## References

### Key Code Locations
- **ReactAgent prompt initialization**: `tinyagent/agents/agent.py:79-85`
- **TinyCodeAgent prompt initialization**: `tinyagent/agents/code_agent.py:213-216`
- **System prompt template**: `tinyagent/prompt.py:3-27`
- **Code system prompt template**: `tinyagent/prompt.py:36-74`
- **Current limited customization**: `tinyagent/agents/code_agent.py:172,215-216`

### GitHub Permalinks
- [prompt.py](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/ca5c6ea603a668200672795ddd249061b67e5547/tinyagent/prompt.py)
- [agent.py](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/ca5c6ea603a668200672795ddd249061b67e5547/tinyagent/agents/agent.py)
- [code_agent.py](https://github.com/alchemiststudiosDOTai/tinyAgent/blob/ca5c6ea603a668200672795ddd249061b67e5547/tinyagent/agents/code_agent.py)

### Test Coverage
- **Prompt generation tests**: `tests/api_test/test_agent.py:130-136`
- **Prompt immutability tests**: `tests/api_test/test_agent.py:388-398`

### Documentation Examples
- **File reading pattern**: `documentation/modules/tools.md` - shows read_file tool example
- **Configuration examples**: `.deployment-config` and `.env` file handling patterns