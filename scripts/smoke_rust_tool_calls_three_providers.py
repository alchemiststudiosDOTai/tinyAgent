#!/usr/bin/env python3
"""Smoke test: 3 sequential tool-call turns via Rust binding across 3 providers."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

from tinyagent._alchemy import openai_completions_stream

load_dotenv()

TOOLS: list[dict[str, Any]] = [
    {
        "name": "add",
        "description": "Add two numbers. Returns the sum.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "multiply",
        "description": "Multiply two numbers. Returns the product.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
    {
        "name": "subtract",
        "description": "Subtract b from a. Returns a - b.",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    },
]

PROVIDERS: list[dict[str, Any]] = [
    {
        "label": "OpenRouter",
        "model": {
            "id": "google/gemini-2.0-flash-001",
            "provider": "openrouter",
            "api": "openai-completions",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
        },
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
    },
    {
        "label": "MiniMax",
        "model": {
            "id": "MiniMax-M2.5",
            "provider": "minimax",
            "api": "minimax-completions",
            "base_url": "https://api.minimax.io/v1/chat/completions",
        },
        "api_key": os.getenv("MINIMAX_API_KEY", ""),
    },
    {
        "label": "Chutes",
        "model": {
            "id": os.getenv("CHUTES_MODEL", "Qwen/Qwen3-Coder-Next-TEE"),
            "provider": "chutes",
            "api": "openai-completions",
            "base_url": "https://llm.chutes.ai/v1/chat/completions",
        },
        "api_key": os.getenv("CHUTES_API_KEY", ""),
    },
]

SYSTEM = (
    "You are a calculator. You MUST use exactly one tool per turn. "
    "Never do arithmetic in your head. "
    "Step 1: add(10, 5). Step 2: multiply(result, 3). Step 3: subtract(result, 7). "
    "After all 3 tool calls, respond with the final number."
)

PROMPT = "Compute (10 + 5) * 3 - 7. Do it step by step, one tool call per turn."


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    a, b = float(arguments["a"]), float(arguments["b"])
    if name == "add":
        result = a + b
    elif name == "multiply":
        result = a * b
    elif name == "subtract":
        result = a - b
    else:
        result = 0.0
    return str(result)


def normalize_args(raw: Any) -> dict[str, Any]:
    """Ensure arguments are a dict, parsing from string if needed."""
    if isinstance(raw, str):
        print(f"      !! WARNING: arguments is str, not dict: {raw!r}")
        parsed = json.loads(raw) if raw else {}
        return parsed if isinstance(parsed, dict) else {}
    if isinstance(raw, dict):
        return raw
    return {}


def do_turn(model: dict[str, Any], api_key: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Run one turn. Returns the assistant result dict."""
    context: dict[str, Any] = {
        "system_prompt": SYSTEM,
        "messages": messages,
        "tools": TOOLS,
    }
    options: dict[str, Any] = {"api_key": api_key}

    handle = openai_completions_stream(model, context, options)
    while handle.next_event() is not None:
        pass
    result: dict[str, Any] = handle.result()
    return result


def run_provider(label: str, model: dict[str, Any], api_key: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  PROVIDER: {label}")
    print(f"  model:    {model['id']}")
    print(f"  api:      {model['api']}")
    print(f"{'=' * 60}")

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": [{"type": "text", "text": PROMPT}]}
    ]

    for turn in range(1, 4):
        print(f"\n  --- Turn {turn} ---")
        result = do_turn(model, api_key, messages)

        stop_reason = result.get("stop_reason")
        content: list[dict[str, Any]] = result.get("content", [])
        tool_calls = [c for c in content if c.get("type") == "tool_call"]
        text_blocks = [c.get("text", "") for c in content if c.get("type") == "text"]
        text = " ".join(t for t in text_blocks if t).strip()

        print(f"  stop_reason: {stop_reason}")

        if text:
            print(f"  text:        {text[:200]}")

        if not tool_calls:
            print("  (no tool calls)")
            if turn < 3:
                print(f"  !! Model stopped early at turn {turn}")
            break

        tc = tool_calls[0]
        name: str = tc.get("name", "?")
        args = normalize_args(tc.get("arguments", {}))
        args_type = type(args).__name__
        tc_id: str = tc.get("id", "")

        print(f"  tool:        {name}")
        print(f"  args:        {args}")
        print(f"  args type:   {args_type}")
        print(f"  tool_id:     {tc_id}")

        tool_result = execute_tool(name, args)
        print(f"  result:      {tool_result}")

        # Append assistant + tool_result to messages for next turn
        messages.append({"role": "assistant", "content": content, "stop_reason": stop_reason})
        messages.append(
            {
                "role": "tool_result",
                "tool_call_id": tc_id,
                "tool_name": name,
                "content": [{"type": "text", "text": tool_result}],
            }
        )
    else:
        # After 3 tool turns, get final answer
        print("\n  --- Final turn ---")
        result = do_turn(model, api_key, messages)
        content = result.get("content", [])
        text_blocks = [c.get("text", "") for c in content if c.get("type") == "text"]
        text = " ".join(t for t in text_blocks if t).strip()
        print(f"  stop_reason: {result.get('stop_reason')}")
        print(f"  answer:      {text[:200]}")

    print("\n  RESULT: PASS")


def main() -> None:
    for p in PROVIDERS:
        api_key: str = p["api_key"]
        if not api_key:
            print(f"\nSKIPPED {p['label']}: no API key")
            continue
        try:
            run_provider(p["label"], p["model"], api_key)
        except Exception as e:
            print(f"\n  FAILED {p['label']}: {e}")


if __name__ == "__main__":
    main()
