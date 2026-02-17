"""Reasoning example for tinyagent using alchemy-llm's Rust implementation of
OpenAI-compatible streaming completions."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from tinyagent import Agent, AgentOptions
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions


async def main() -> None:
    load_dotenv()

    model = OpenAICompatModel(
        provider="openrouter",
        id="deepseek/deepseek-r1",
        base_url="https://openrouter.ai/api/v1/chat/completions",
        headers={"X-title": "tinyagent reasoning example"},
        reasoning=True,
    )
    agent = Agent(AgentOptions(stream_fn=stream_alchemy_openai_completions))
    agent.set_system_prompt(
        "You are a helpful assistant that can reason step by step. "
        "Answer the question at the end after reasoning."
    )
    agent.set_model(model)

    prompt = "Question: If I have 3 apples and I buy 2 more, how many apples do I have?"

    assistant_message = await agent.prompt(prompt)

    output_path = Path(__file__).parent / "example_reasoning_output.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(assistant_message, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    asyncio.run(main())
