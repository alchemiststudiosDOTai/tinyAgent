# Bug: MiniMax multi-turn tool calls return empty arguments

## Summary

When using `alchemy-llm` 0.1.5 with `minimax-completions` API dispatch, tool call arguments are correctly parsed on the first turn but come back as empty `{}` on subsequent turns.

## Reproduction

Model: `MiniMax-M2.5` via `minimax-completions` API.
Prompt: step-by-step arithmetic requiring one tool call per turn (add, multiply, subtract).

### Turn 1 (works)

```
stop_reason: tool_calls
tool:        add
args:        {'a': 10, 'b': 5}     <-- correct
tool_id:     call_function_hsex1yybdpoc_1
```

### Turn 2 (broken)

```
stop_reason: tool_calls
tool:        multiply
args:        {}                     <-- empty, should be {'a': 15, 'b': 3}
tool_id:     call_function_l9zhy68u9i7n_1
```

Execution fails with `KeyError: 'a'` because arguments are missing.

## Context

- Same prompt/tools work correctly on Turn 1 for MiniMax, and work correctly on all turns for OpenRouter and Chutes (both using `openai-completions`).
- The issue is specific to `minimax-completions` on multi-turn (turn 2+).
- Likely cause: the SSE streaming argument accumulation logic for MiniMax is not carrying forward or parsing `function.arguments` deltas correctly on follow-up tool calls.

## Tested via

Direct Rust binding call (`tinyagent._alchemy.openai_completions_stream`), no Python provider layer involved. Test script attached below.

## Environment

- alchemy-llm: 0.1.5
- MiniMax model: MiniMax-M2.5
- Base URL: https://api.minimax.io/v1/chat/completions

## Workaround

None currently. The arguments are empty before they reach the Python side, so no Python-side normalization can recover them.
