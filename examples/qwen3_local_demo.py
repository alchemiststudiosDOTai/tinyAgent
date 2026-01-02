"""
Qwen3-0.6B Sushi Coder Local Demo

ReactAgent using Qwen3-0.6B Sushi Coder on localhost:8000.

Usage:
    1. Start local server: vllm serve Qwen3-0.6B-Sushi-Coder --host 0.0.0.0 --port 8000
    2. Run: python examples/qwen3_local_demo.py
"""

from __future__ import annotations

import asyncio
import os

os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/v1"
os.environ["OPENAI_API_KEY"] = "not-needed"

from tinyagent import ReactAgent, tool


@tool
def double(x: float) -> float:
    """Double the input number."""
    return x * 2


async def main() -> None:
    agent = ReactAgent(tools=[double], model="Qwen3-0.6B-Sushi-Coder")
    result = await agent.run("What is 5 doubled?", verbose=True)
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
