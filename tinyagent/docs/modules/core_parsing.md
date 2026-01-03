---
title: LLM Response Parsing
path: core/parsing.py
type: file
depth: 1
description: Robust JSON parsing for LLM responses with wrapper handling
exports: [parse_json_response, strip_llm_wrappers]
seams: [M]
---

# core/parsing.py

## Where
`/Users/tuna/tinyAgent/tinyagent/core/parsing.py`

## What
Robustly parses JSON responses from LLMs, handling common extraneous elements like think tags and markdown code fences. Normalizes LLM responses for reliable downstream processing.

## How

### Key Functions

**parse_json_response(text: str) -> dict[str, Any] | None**
- Main entry point for parsing LLM responses
- Strips common wrappers using `strip_llm_wrappers`
- Attempts to parse cleaned text as JSON
- Returns dictionary if successful, None if parsing fails

**strip_llm_wrappers(text: str) -> str**
- Cleans raw LLM output using regular expressions
- Removes ```think``` blocks (internal reasoning)
- Removes stray opening/closing think tags
- Extracts content from markdown code fences:
  - `` ```json ... ``` ``
  - `` ``` ... ``` ``
- Returns cleaned text ready for JSON parsing

**Patterns Handled:**
- Thinking blocks: ````` ... ``````
- Code fences with language specifier: ```json ... ```
- Code fences without specifier: ``` ... ```
- Mixed content with conversational filler

## Why

**Design Rationale:**
- **LLM Inconsistency**: LLMs frequently include conversational filler alongside structured data
- **Normalization**: Ensures downstream components receive clean, parsable JSON
- **Flexibility**: Regex handles variations in wrapper patterns
- **Reliability**: Prevents parsing errors from common LLM output quirks

**Architectural Role:**
- Intermediary layer between raw LLM text and JSON consumers
- Crucial for system reliability when processing LLM responses
- Used by adapters and agents to extract structured data
- Reduces chances of parsing errors in subsequent processing

**Dependencies:**
- `json`: JSON parsing
- `re`: Regular expressions for pattern matching
- `typing`: Type hints
