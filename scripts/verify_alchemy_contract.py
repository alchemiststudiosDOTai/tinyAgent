#!/usr/bin/env python3
"""Verify that EVERY field in the alchemy contract is sent.

This proves that the Rust alchemy binding returns all required fields:
  Usage: input, output, cache_read, cache_write, total_tokens, cost
  Cost: input, output, cache_read, cache_write, total

Required env vars:
  - OPENROUTER_API_KEY

Optional env vars:
  - OPENROUTER_MODEL (default: moonshotai/kimi-k2.5)
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from tinyagent.agent_types import Context
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions


def load_dotenv_inline(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


async def main() -> None:
    load_dotenv_inline()

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    if not api_key:
        raise SystemExit("Missing OPENROUTER_API_KEY")

    model = OpenAICompatModel(
        provider="openrouter",
        id=os.environ.get("OPENROUTER_MODEL", "moonshotai/kimi-k2.5"),
        base_url="https://openrouter.ai/api/v1/chat/completions",
        headers={"X-Title": "tinyagent-contract-verify"},
    )

    ctx = Context(
        system_prompt="You are concise.",
        messages=[
            {
                "role": "user",
                "content": [{"type": "text", "text": "Reply in one short sentence: hello."}],
            }
        ],
    )

    resp = await stream_alchemy_openai_completions(
        model,
        ctx,
        {
            "api_key": api_key,
            "temperature": 0.0,
            "max_tokens": 80,
        },
    )

    final = await resp.result()

    print("=" * 70)
    print("CONTRACT VERIFICATION: All required fields received")
    print("=" * 70)

    usage = final.get("usage")
    if not isinstance(usage, dict):
        raise RuntimeError(f"usage is not a dict: {usage}")

    print("\nUSAGE FIELDS (required: input, output, cache_read, cache_write, total_tokens, cost):")
    print("-" * 70)

    required_usage_keys = ["input", "output", "cache_read", "cache_write", "total_tokens", "cost"]
    for key in required_usage_keys:
        value = usage.get(key)
        if key not in usage:
            print(f"❌ {key:<15} MISSING!")
        else:
            print(f"✓ {key:<15} {value}")

    cost = usage.get("cost")
    if not isinstance(cost, dict):
        raise RuntimeError(f"usage.cost is not a dict: {cost}")

    print("\nCOST FIELDS (required: input, output, cache_read, cache_write, total):")
    print("-" * 70)

    required_cost_keys = ["input", "output", "cache_read", "cache_write", "total"]
    for key in required_cost_keys:
        value = cost.get(key)
        if key not in cost:
            print(f"❌ {key:<15} MISSING!")
        else:
            print(f"✓ {key:<15} {value}")

    print("\n" + "=" * 70)

    missing_usage = [k for k in required_usage_keys if k not in usage]
    missing_cost = [k for k in required_cost_keys if k not in cost]

    if missing_usage or missing_cost:
        raise RuntimeError(
            f"Contract violation! Missing keys:\n  Usage: {missing_usage}\n  Cost: {missing_cost}"
        )

    print("✓ ALL CONTRACT FIELDS PRESENT AND VALIDATED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
