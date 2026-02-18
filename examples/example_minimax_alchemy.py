#!/usr/bin/env python3
"""Example: TinyAgent + MiniMax via the Rust alchemy binding.

Prereqs:
  - Build extension from repo root: maturin develop --release
  - Set MINIMAX_API_KEY in env or .env

Run:
  uv run python examples/example_minimax_alchemy.py
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv

from tinyagent import Agent, AgentOptions
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1/chat/completions"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.5"


async def main() -> None:
    load_dotenv()

    if not os.getenv("MINIMAX_API_KEY"):
        print("Missing MINIMAX_API_KEY. Add it to your env or .env file.")
        return

    agent = Agent(AgentOptions(stream_fn=stream_alchemy_openai_completions))
    agent.set_system_prompt("You are a helpful assistant. Be concise.")
    agent.set_model(
        OpenAICompatModel(
            provider="minimax",
            api="minimax-completions",
            id=os.getenv("MINIMAX_MODEL", DEFAULT_MINIMAX_MODEL),
            base_url=os.getenv("MINIMAX_BASE_URL", DEFAULT_MINIMAX_BASE_URL),
        )
    )

    print("MiniMax chat (type 'quit' to exit)")
    print("-" * 36)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            return

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "q"}:
            return

        print("Assistant: ", end="", flush=True)
        async for delta in agent.stream_text(user_input):
            print(delta, end="", flush=True)
        print()


if __name__ == "__main__":
    asyncio.run(main())
