#!/usr/bin/env python3
"""Smoke test: verify usage from OpenRouter + Chutes via Rust alchemy binding.

This script intentionally uses the same Rust stream path for both providers:
    tinyagent.alchemy_provider.stream_alchemy_openai_completions

Required env vars:
  - OPENROUTER_API_KEY
  - CHUTES_API_KEY

Optional env vars:
  - OPENROUTER_MODEL (default: moonshotai/kimi-k2.5)
  - CHUTES_MODEL (default: deepseek-ai/DeepSeek-V3.1)
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


async def run_once(label: str, model: OpenAICompatModel, api_key: str) -> dict[str, object]:
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
    usage = final.get("usage") if isinstance(final, dict) else None
    stop_reason = final.get("stop_reason") if isinstance(final, dict) else None

    return {
        "label": label,
        "stop_reason": stop_reason,
        "usage": usage if isinstance(usage, dict) else {},
    }


def usage_cell(usage: dict[str, object], key: str) -> str:
    v = usage.get(key, 0)
    return str(v if isinstance(v, int | float) else 0)


async def main() -> None:
    load_dotenv_inline()

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    chutes_key = os.environ.get("CHUTES_API_KEY", "").strip()

    if not openrouter_key:
        raise SystemExit("Missing OPENROUTER_API_KEY")
    if not chutes_key:
        raise SystemExit("Missing CHUTES_API_KEY")

    openrouter_model = OpenAICompatModel(
        provider="openrouter",
        id=os.environ.get("OPENROUTER_MODEL", "moonshotai/kimi-k2.5"),
        base_url="https://openrouter.ai/api/v1/chat/completions",
        headers={"X-Title": "tinyagent-rust-smoke"},
    )

    chutes_model = OpenAICompatModel(
        provider="chutes",
        id=os.environ.get("CHUTES_MODEL", "deepseek-ai/DeepSeek-V3.1"),
        base_url="https://llm.chutes.ai/v1/chat/completions",
    )

    print("Using Rust path for both providers: stream_alchemy_openai_completions\n")

    results = []
    results.append(await run_once("OpenRouter", openrouter_model, openrouter_key))
    results.append(await run_once("Chutes", chutes_model, chutes_key))

    print(
        f"{'Provider':<12} {'Stop':<10} {'Input':>7} {'Output':>7} {'CacheRead':>10} {'Total':>7}"
    )
    print("-" * 60)
    for r in results:
        usage = r["usage"]
        assert isinstance(usage, dict)
        print(
            f"{r['label']:<12} {str(r['stop_reason']):<10} "
            f"{usage_cell(usage, 'input'):>7} {usage_cell(usage, 'output'):>7} "
            f"{usage_cell(usage, 'cache_read'):>10} {usage_cell(usage, 'total_tokens'):>7}"
        )


if __name__ == "__main__":
    asyncio.run(main())
