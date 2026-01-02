# tinyagent.core.parsing

JSON parsing for LLM responses. Strips common wrappers that local models emit.

## Problem

Local models (Qwen3, Llama, DeepSeek) wrap JSON responses in:
- `<think>...</think>` reasoning blocks
- Markdown code fences (```json ... ```)

Raw `json.loads()` fails, causing retry loops until step limit.

## Functions

**parse_json_response(text: str) -> dict | None**
Main entry. Strips wrappers then parses JSON. Returns None on failure.

**strip_llm_wrappers(text: str) -> str**
Removes `<think>` tags (full blocks and stray tags), extracts content from code fences.

## Examples

```python
from tinyagent.core.parsing import parse_json_response

# All return {"answer": "10"}
parse_json_response('{"answer": "10"}')
parse_json_response('<think>\n</think>\n{"answer": "10"}')
parse_json_response('```json\n{"answer": "10"}\n```')
parse_json_response('<think>reasoning here</think>\n```json\n{"answer": "10"}\n```')
```

## Location

- Module: `tinyagent/core/parsing.py`
- Exported from: `tinyagent.core`

## Used in

- `ReactAgent._process_step()` line 167
- `ReactAgent._attempt_final_answer()` line 286
