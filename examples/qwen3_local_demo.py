"""
Qwen3-0.6B Sushi Coder Local Demo

ReactAgent using Qwen3-0.6B Sushi Coder on localhost:8000.

Usage:
    1. Start local server: vllm serve Qwen3-0.6B-Sushi-Coder --host 0.0.0.0 --port 8000
    2. Run: python examples/qwen3_local_demo.py
"""

from __future__ import annotations

import asyncio
import json
import os

os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/v1"
os.environ["OPENAI_API_KEY"] = "not-needed"

from tinyagent import ReactAgent, tool


@tool
def double(x: float) -> float:
    """Double the input number."""
    return x * 2


class LoggingReactAgent(ReactAgent):
    """ReactAgent that logs all sent messages and received responses."""

    async def _chat(self, messages: list[dict[str, str]], temperature: float) -> str:
        """Log messages sent to LLM and response received."""
        print("\n" + "=" * 60)
        print("SENT TO MODEL:")
        print("-" * 40)
        print(json.dumps(messages, indent=2))
        print("=" * 60)

        response = await super()._chat(messages, temperature)

        print("\n" + "=" * 60)
        print("RECEIVED FROM MODEL:")
        print("-" * 40)
        print(response)
        print("=" * 60 + "\n")

        return response


async def main() -> None:
    agent = LoggingReactAgent(tools=[double], model="qwen3-1.7b-reasoning")
    result = await agent.run("What is 5 doubled?", verbose=True)
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
