#!/usr/bin/env python3
"""Verify that ALL usage fields are preserved through the Agent layer.

This proves that when using Agent.prompt() or Agent.stream(), the final
assistant message contains ALL contract fields from the alchemy binding:
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

from tinyagent.agent import Agent, AgentOptions
from tinyagent.agent_types import ThinkingLevel
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
        headers={"X-Title": "tinyagent-agent-contract-verify"},
    )

    agent = Agent(
        AgentOptions(
            stream_fn=stream_alchemy_openai_completions,
            get_api_key=lambda _provider: api_key,
        )
    )
    agent.set_model(model)
    agent.set_system_prompt("You are concise.")
    agent.set_thinking_level(ThinkingLevel.OFF)

    print("=" * 70)
    print("CONTRACT VERIFICATION: All required fields through Agent.prompt()")
    print("=" * 70)

    final_message = await agent.prompt("Reply in one short sentence: hello.")

    print(f"\n✓ Got assistant message with role: {final_message.get('role')}")

    usage = final_message.get("usage")
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

    print("\n" + "=" * 70)
    print("CONTRACT VERIFICATION: All required fields through Agent.stream()")
    print("=" * 70)

    events = []
    async for event in agent.stream("Reply in one short sentence: hello again."):
        events.append(event)

    print(f"\n✓ Got {len(events)} events from stream")

    agent_end_event = None
    for event in events:
        if getattr(event, "type", None) == "agent_end":
            agent_end_event = event
            break

    if not agent_end_event:
        raise RuntimeError("No agent_end event found")

    messages = getattr(agent_end_event, "messages", [])
    assistant_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            assistant_msg = msg
            break

    if not assistant_msg:
        raise RuntimeError("No assistant message found in agent_end event")

    usage = assistant_msg.get("usage")
    if not isinstance(usage, dict):
        raise RuntimeError(f"usage is not a dict: {usage}")

    print("\nUSAGE FIELDS (required: input, output, cache_read, cache_write, total_tokens, cost):")
    print("-" * 70)

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

    print("✓ ALL CONTRACT FIELDS PRESENT AND VALIDATED (stream)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
