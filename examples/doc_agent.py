"""
Documentation Analysis Agent with Qwen3

ReactAgent using Qwen3 on localhost to analyze documentation files with file system tools.

Tools:
    - glob: Find files matching a pattern
    - grep: Search for patterns within files
    - read_file: Read file contents

Usage:
    1. Start local server: vllm serve Qwen3-0.6B-Sushi-Coder --host 0.0.0.0 --port 8000
    2. Run: python examples/doc_agent.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from tinyagent import ReactAgent, tool


@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file.

    Args:
        file_path: Path to the file to read

    Returns:
        File contents as a string
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File '{file_path}' does not exist"

    if not path.is_file():
        return f"Error: '{file_path}' is not a file"

    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        return f"Error reading file: {e}"


@tool
def glob(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g., '*.py', '**/*.md')
        path: Root directory to search (default: current directory)

    Returns:
        JSON string of matching file paths sorted by modification time
    """
    search_path = Path(path)
    if not search_path.exists():
        return json.dumps({"error": f"Path '{path}' does not exist"})

    matches = sorted(search_path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return json.dumps([str(m) for m in matches])


class LoggingReactAgent(ReactAgent):
    """ReactAgent with clean logging output."""

    async def _chat(self, temperature: float):
        """Log messages and responses in a clean format."""
        print("\n" + "─" * 70)
        print("📤 TO MODEL")
        print("─" * 70)

        for msg in self._memory.to_list():
            role = msg["role"].upper()
            content = msg.get("content", "")
            print(f"\n[{role}]")
            if content:
                print(content)
            if "tool_calls" in msg:
                print(f"[TOOL CALLS: {msg['tool_calls']}]")

        print("\n" + "─" * 70)
        print("📥 FROM MODEL")
        print("─" * 70)

        response = await super()._chat(temperature)

        print(f"\n{response}")
        print("─" * 70 + "\n")

        return response


async def main() -> None:
    agent = LoggingReactAgent(
        tools=[read_file, glob],
        model="openai/gpt-4.1-mini",
        max_tokens=4000,
    )

    result = await agent.run(
        "Find all Python files in the tinyagent directory and read the first one to understand what it does.",
        verbose=True,
        max_steps=10,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
