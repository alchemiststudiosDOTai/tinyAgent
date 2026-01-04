---
title: Prompt Templates
path: prompts/templates.py
type: file
depth: 1
description: Core prompt templates defining agent behavior, interaction formats, and output structures
exports: [SYSTEM, BAD_JSON, CODE_SYSTEM]
seams: [M]
---

# prompts/templates.py

## Where
`/Users/tuna/tinyAgent/tinyagent/prompts/templates.py`

## What
Defines core prompt templates that guide agent behavior and interaction format. Sets rules, roles, available tools, and expected output formats for language models.

## How

### Key Templates

**SYSTEM**
Primary system prompt for general tool-using assistant:
- **Role Definition**: "You are a tool-using assistant."
- **Tools Placeholder**: `{tools}` for injecting available tools
- **Critical Rules**:
  - "NEVER guess or make up information"
  - "ALWAYS call glob, grep, or read_file first"
  - "Output ONLY valid JSON"
- **Response Format**: JSON structure for tool calls and final answers
- **Example Interaction**: Demonstrates correct usage
- **Instructions**: Numbered list summarizing workflow

**BAD_JSON**
Error recovery prompt for invalid JSON:
- Provides error message explaining problem
- Shows valid JSON format examples
- Instructs agent to correct output

**CODE_SYSTEM**
System prompt for Python code execution agent:
- **Role Definition**: "You are a Python code execution agent."
- **Available Tools**: `{helpers}` placeholder for Python helper functions
- **Response Format**:
  - Single Python code block
  - Reasoning in comments
  - Single call to `final_answer()`
- **Examples**:
  - Simple calculations
  - Tool usage
  - Multi-step problems
- **Constraints**: Rules for code output
- **Think Instruction**: Encourages step-by-step reasoning

## Why

**Design Rationale:**
- **Behavioral Control**: Primary mechanism for programming LLM behavior
- **Modularity**: Centralized templates for easy modification
- **Consistency**: Ensures all agents adhere to same patterns
- **Structured Output**: Enforces JSON or Python code formats
- **Error Recovery**: BAD_JSON enables self-correction

**Architectural Role:**
- **Agent Instructions**: Loaded by agent orchestration logic
- **Behavior Definition**: "Constitution" for agent operations
- **Format Enforcement**: Ensures parseable, predictable outputs
- **Multi-Agent Support**: Different templates for different agent types

**Dependencies:**
- None (pure string constants)
- Used by: agents, prompts loader
