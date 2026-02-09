"""Live test: does prompt caching actually work with OpenRouter?

Run:
  OPENROUTER_API_KEY=... uv run python test_cache_live.py

Expected (OpenRouter):
- The second turn in the cached run should report usage["cacheRead"] > 0.
- usage["cacheWrite"] may remain 0 due to OpenRouter not reporting cache writes.
"""

from __future__ import annotations

import asyncio
import time
from typing import cast

from dotenv import load_dotenv

from tinyagent import Agent, AgentOptions, OpenRouterModel, stream_openrouter
from tinyagent.agent_types import AgentMessage, JsonObject

load_dotenv()


def ts() -> str:
    return f"[{time.strftime('%H:%M:%S')}]"


def _usage(msg: AgentMessage) -> JsonObject:
    usage = msg.get("usage")
    if isinstance(usage, dict):
        return cast(JsonObject, usage)
    return {}


def _cache_read(usage: JsonObject) -> int:
    value = usage.get("cacheRead", 0)
    if isinstance(value, int | float):
        return int(value)
    return 0


async def main() -> None:
    print(f"{ts()} Starting cache test", flush=True)

    # Long system prompt to exceed Claude 3.5 Haiku's cached-prefix minimum.
    # OpenRouter/Anthropic requires >= 2,048 tokens in the cacheable prefix for this model.
    system_prompt = (
        "You are a helpful assistant.\n"
        + ("filler " * 2600)
        + "\nAlways reply in one short sentence."
    )

    model = OpenRouterModel(
        id="anthropic/claude-3.5-haiku",
        # Try to force OpenRouter to use Anthropic directly (not Bedrock), since
        # prompt caching may not be supported on all upstream providers.
        openrouter_provider={"order": ["Anthropic"], "allow_fallbacks": False},
    )

    # --- Run WITHOUT caching ---
    print(f"\n{ts()} === RUN 1: WITHOUT caching ===", flush=True)

    agent_no_cache = Agent(
        AgentOptions(
            stream_fn=stream_openrouter,
            enable_prompt_caching=False,
        )
    )
    agent_no_cache.set_model(model)
    agent_no_cache.set_system_prompt(system_prompt)

    print(f"{ts()} Sending turn 1 (no cache)...", flush=True)
    r1 = await agent_no_cache.prompt("What is the capital of France?")
    usage1 = _usage(r1)
    print(f"{ts()} Turn 1 done. usage={usage1}", flush=True)

    print(f"{ts()} Sending turn 2 (no cache)...", flush=True)
    r2 = await agent_no_cache.prompt("What is the capital of Germany?")
    usage2 = _usage(r2)
    print(f"{ts()} Turn 2 done. usage={usage2}", flush=True)

    # --- Run WITH caching ---
    print(f"\n{ts()} === RUN 2: WITH caching ===", flush=True)

    agent_cached = Agent(
        AgentOptions(
            stream_fn=stream_openrouter,
            enable_prompt_caching=True,
        )
    )
    agent_cached.set_model(model)
    agent_cached.set_system_prompt(system_prompt)

    print(f"{ts()} Sending turn 1 (cached)...", flush=True)
    r3 = await agent_cached.prompt("What is the capital of France?")
    usage3 = _usage(r3)
    print(f"{ts()} Turn 1 done. usage={usage3}", flush=True)

    print(f"{ts()} Sending turn 2 (cached)...", flush=True)
    r4 = await agent_cached.prompt("What is the capital of Germany?")
    usage4 = _usage(r4)
    print(f"{ts()} Turn 2 done. usage={usage4}", flush=True)

    # --- Summary ---
    print(f"\n{ts()} === SUMMARY ===", flush=True)

    def fmt(usage: JsonObject) -> str:
        cache_read = usage.get("cacheRead", "N/A")
        cache_write = usage.get("cacheWrite", "N/A")
        return f"cacheRead={cache_read}, cacheWrite={cache_write}"

    print(f"  No-cache turn 2:  {fmt(usage2)}")
    print(f"  Cached   turn 1:  {fmt(usage3)}")
    print(f"  Cached   turn 2:  {fmt(usage4)}")

    if _cache_read(usage4) > 0:
        print("\n  RESULT: Caching is WORKING -- turn 2 got cache hits")
    else:
        print("\n  RESULT: Caching does NOT appear to be working -- no cache reads detected")


if __name__ == "__main__":
    asyncio.run(main())
