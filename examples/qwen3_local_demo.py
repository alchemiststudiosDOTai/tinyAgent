"""
Qwen3 Local Demo with File System Tools

ReactAgent using Qwen3 on localhost:8000 with glob, grep, and read_file tools.

Tools:
    - glob: Find files matching a pattern
    - grep: Search for patterns within files
    - read_file: Read file contents

Usage:
    1. Start local server: vllm serve Qwen3-0.6B-Sushi-Coder --host 0.0.0.0 --port 8000
    2. Run: python examples/qwen3_local_demo.py
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

os.environ["OPENAI_BASE_URL"] = "http://localhost:8000/v1"
os.environ["OPENAI_API_KEY"] = "not-needed"

from tinyagent import ReactAgent, tool


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


@tool
def grep(pattern: str, path: str = ".", glob_pattern: str = "*.py") -> str:
    """Search for a pattern in files using regex.

    Args:
        pattern: Regular expression pattern to search for
        path: Root directory to search (default: current directory)
        glob_pattern: File pattern to match (default: '*.py')

    Returns:
        JSON string with file paths and matching lines
    """
    import re

    search_path = Path(path)
    if not search_path.exists():
        return json.dumps({"error": f"Path '{path}' does not exist"})

    results: dict[str, list[dict[str, int | str]]] = {}
    regex = re.compile(pattern)

    for file_path in search_path.rglob(glob_pattern):
        if file_path.is_file():
            try:
                with open(file_path, encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            file_str = str(file_path)
                            if file_str not in results:
                                results[file_str] = []
                            results[file_str].append(
                                {"line": line_num, "content": line.rstrip("\n")}
                            )
            except (OSError, UnicodeDecodeError):
                continue

    return json.dumps(results)


@tool
def read_file(file_path: str) -> str:
    """Read the contents of a file.

    Args:
        file_path: Path to the file to read

    Returns:
        File contents as a string
    """
    path = Path(file_path)
    print(f"Reading filesssssssssssssssssssssssssssssssssssssss: {file_path}")
    if not path.exists():
        return f"Error: File '{file_path}' does not exist"

    if not path.is_file():
        return f"Error: '{file_path}' is not a file"

    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        return f"Error reading file: {e}"


class LoggingReactAgent(ReactAgent):
    """ReactAgent with clean logging output."""

    async def _chat(self, messages: list[dict[str, str]], temperature: float) -> str:
        """Log messages and responses in a clean format."""
        print("\n" + "─" * 70)
        print("📤 TO MODEL")
        print("─" * 70)

        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            print(f"\n[{role}]")
            print(content)

        print("\n" + "─" * 70)
        print("📥 FROM MODEL")
        print("─" * 70)

        response = await super()._chat(messages, temperature)

        print(f"\n{response}")
        print("─" * 70 + "\n")

        return response


async def main() -> None:
    agent = LoggingReactAgent(
        tools=[glob],
        model="qwen3-1.7b-reasoning",
        max_tokens=2048,
    )

    result = await agent.run(
        "Find all Python files in the tinyagent directory.", verbose=True, max_steps=20
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
