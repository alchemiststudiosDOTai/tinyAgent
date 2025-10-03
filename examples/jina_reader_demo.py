"""
Jina Reader Demo - Scrape and summarize web content via ReactAgent

This interactive example shows how to:
- Expose a simple web scraping tool with `@tool`
- Use the free Jina Reader endpoint (https://r.jina.ai/) to fetch page text
- Let `ReactAgent` summarize results from a given URL

Usage:
    uv venv && source .venv/bin/activate
    uv pip install tiny_agent_os  # if using outside the repo
    python examples/jina_reader_demo.py

Notes:
- The Jina Reader endpoint generally does not require an API key.
- This example avoids external dependencies by using urllib from the stdlib.
"""

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # dotenv is optional for examples
    pass

import os
import sys
import threading
import time
import typing
from contextlib import contextmanager
from typing import Final, Sequence, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tinyagent import ReactAgent, tool
from tinyagent.core.registry import Tool

JINA_READER_BASE: Final[str] = "https://r.jina.ai/"


@tool
def jina_scrape(url: str) -> str:
    """Fetch plaintext content for a given web URL via Jina Reader.

    Args:
        url: Absolute URL to fetch (e.g. "https://example.com").

    Returns:
        The extracted plaintext content.

    Raises:
        ValueError: If the URL looks invalid.
        RuntimeError: On HTTP/network errors.
    """
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("url must start with http:// or https://")

    reader_url = f"{JINA_READER_BASE}{url}"

    headers = {"User-Agent": "tinyAgent/1.0"}
    api_key = os.getenv("JINA_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = Request(reader_url, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:  # nosec B310: fixed host over HTTPS; scheme validated  # type: ignore[arg-type]
            if resp.status != 200:
                raise RuntimeError(f"Jina Reader returned status {resp.status}")
            data = resp.read()
            return data.decode("utf-8", errors="replace")
    except HTTPError as e:  # Fail fast, fail loud
        raise RuntimeError(f"HTTPError from Jina Reader: {e.code} {e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Network error contacting Jina Reader: {e.reason}") from e


@contextmanager
def spinner(label: str = "Searching") -> typing.Iterator[None]:
    stop = threading.Event()

    def _run() -> None:
        sys.stdout.write(f"{label}")
        sys.stdout.flush()
        while not stop.is_set():
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(0.4)
        sys.stdout.write("\n")
        sys.stdout.flush()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=1)


def main() -> None:
    agent = ReactAgent(tools=cast("Sequence[Tool]", [jina_scrape]))

    print("Jina Reader Demo - Interactive Scraper")
    print("=" * 50)
    while True:
        query = input("Enter a URL to scrape (or 'quit'): ").strip()
        if query.lower() == "quit":
            break
        prompt = f"Scrape the content from {query} and provide a concise summary with key points."
        with spinner("Searching"):
            result = agent.run(prompt)
        print(f"\nResult:\n{result}\n")


if __name__ == "__main__":
    main()
