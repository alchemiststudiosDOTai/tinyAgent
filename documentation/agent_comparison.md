# Agent Comparison: ReactAgent vs TinyCodeAgent

This document explains the key differences between the two ReAct (Reasoning + Acting) agents in this project: `agent.py` (ReactAgent) and `code_agent.py` (TinyCodeAgent).

## Overview

Both agents implement ReAct loops for AI-assisted task completion using tools, but they differ in how they interact with and execute tools.

## ReactAgent (agent.py)

- **Approach**: Uses structured JSON payloads to call tools via LLM messages.
- **Tool calls**: LLM outputs JSON with `tool` name, `arguments` dict, and optional `scratchpad` for reasoning.
- **Execution**: Tools are called directly in Python after JSON parsing and validation.
- **Error handling**: Retries with increasing temperature on JSON failures or invalid steps.
- **Safety**: Argument validation via function signatures; no sandbox for execution.
- **Max steps**: 10 (default).
- **Use case**: Best for precise, predefined tool interactions where reliability is key.

## TinyCodeAgent (code_agent.py)

- **Approach**: LLM generates executable Python code blocks that run in a restricted sandbox.
- **Tool calls**: Tools become global functions in the sandbox; LLM writes code to call them.
- **Execution**: Code executes with output captured; `final_answer()` signals completion.
- **Safety**: Strict sandbox limits builtins, imports (configurable extras allowed), and execution environment.
- **Error handling**: Reports execution errors back to LLM as observations; no temperature variation.
- **Max steps**: 6 (default).
- **Use case**: Ideal for flexible, multi-step tasks needing variable logic or computations.

## Key Differences

1. **Tool Invocation**:
   - ReactAgent: Declarative JSON-based calls.
   - TinyCodeAgent: Imperative Python code generation.

2. **Flexibility**:
   - ReactAgent: Fixed tool contracts.
   - TinyCodeAgent: Dynamic, programmable tool use (e.g., loops, conditions, data manipulation).

3. **Reliability/Risk**:
   - ReactAgent: Safer (validated args, no code execution).
   - TinyCodeAgent: More powerful but riskier (sandboxed exec; code injection potential, mitigated by safeguards).

4. **Performance**:
   - ReactAgent: Faster for simple calls; handles JSON errors.
   - TinyCodeAgent: Slower (executes code); better for complex logic; always temperature 0.

Choose ReactAgent for structured, secure tool use. Choose TinyCodeAgent for creative, code-driven problem-solving.
