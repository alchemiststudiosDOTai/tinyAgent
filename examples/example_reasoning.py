"""Reasoning example for tinyagent using alchemy-llm's Rust implementation of
OpenAI-compatible streaming completions.

Demonstrates how reasoning models return separate thinking and text blocks.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TypeGuard

from dotenv import load_dotenv

from tinyagent import Agent, AgentOptions
from tinyagent.agent_types import (
    AssistantContent,
    AssistantMessage,
    TextContent,
    ThinkingContent,
)
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions


def is_thinking_content(block: AssistantContent | None) -> TypeGuard[ThinkingContent]:
    return block is not None and block.get("type") == "thinking"


def is_text_content(block: AssistantContent | None) -> TypeGuard[TextContent]:
    return block is not None and block.get("type") == "text"


def print_reasoning_response(message: AssistantMessage) -> None:
    """Print reasoning and answer blocks separately."""
    content = message.get("content") or []

    thinking_blocks = [b for b in content if is_thinking_content(b)]
    text_blocks = [b for b in content if is_text_content(b)]

    if thinking_blocks:
        print("=== REASONING ===")
        for block in thinking_blocks:
            print(block.get("thinking", ""))
        print()

    if text_blocks:
        print("=== ANSWER ===")
        for block in text_blocks:
            print(block.get("text", ""))
        print()


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

    # Print separated reasoning vs answer
    print_reasoning_response(assistant_message)

    # Also save raw JSON for inspection
    output_path = Path(__file__).parent / "example_reasoning_output.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(assistant_message, f, indent=2)
        f.write("\n")

    print(f"Raw output saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
