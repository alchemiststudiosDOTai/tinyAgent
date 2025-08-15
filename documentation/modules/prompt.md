# Prompt Templates Documentation

The prompt templates in TinyAgent define how agents interact with the LLM and guide their behavior.

## Overview

Prompt templates provide:
- System instructions for agent behavior
- Tool descriptions for LLM understanding
- Error correction guidance
- Consistent response formatting

## System Prompt Template

The main system prompt (`SYSTEM`) in `prompt.py` includes:

### Role Definition
Clear identification as a problem-solving assistant with tool access.

### Available Tools Section
Dynamically generated list of registered tools with:
- Tool names
- Descriptions from docstrings
- Function signatures

### Response Format
Strict JSON format requirements:
1. Tool usage with reasoning:
   ```json
   {"scratchpad": "Step-by-step thinking", "tool": "tool_name", "arguments": {"param": "value"}}
   ```
2. Final answer provision:
   ```json
   {"scratchpad": "Based on results", "answer": "Comprehensive answer"}
   ```

### Examples
Concrete examples of proper usage patterns.

## Code Agent Prompt

The code agent prompt (`CODE_SYSTEM`) guides Python code generation:

### Role Definition
Identification as a Python code execution agent.

### Task Description
Instructions to solve problems through code.

### Requirements
- Output only Python code blocks
- Include reasoning as comments
- Call `final_answer()` with results
- Think step by step

### Format Specification
Exact format for code blocks with:
- Step-by-step comments
- Tool usage examples
- Final answer pattern

### Example
Complete working example of code generation.

## Error Correction Prompts

### BAD_JSON
Used when JSON parsing fails:
- Examples of valid JSON formats
- Request for correction
- Guidance on proper structure

## Template Variables

### `{tools}`
Replaced with formatted list of available tools:
```
- tool_name: tool_description | args=(signature)
```

### `{helpers}`
Replaced with list of code agent helpers:
```
tool_name1, tool_name2, ...
```

## Customization

System prompts can be customized by:
1. Modifying the templates in `prompt.py`
2. Extending agents with `system_suffix` parameter
3. Creating custom agent subclasses

## Best Practices

- Keep prompts focused and specific
- Provide clear examples
- Use consistent formatting
- Include error recovery guidance
- Balance detail with conciseness
