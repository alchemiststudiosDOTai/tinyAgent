"""Live integration test for the tool-call type harness."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv


def _has_supported_api_key() -> bool:
    return any(
        os.getenv(key)
        for key in (
            "OPENROUTER_API_KEY",
            "CHUTES_API_KEY",
            "MINIMAX_API_KEY",
        )
    )


def test_tool_call_types_harness_runs_end_to_end() -> None:
    """Run the harness as a real integration test when explicitly enabled.

    This test is opt-in because it performs a real network call and requires
    provider credentials.
    """

    if os.getenv("RUN_LIVE_HARNESS") != "1":
        pytest.skip("Set RUN_LIVE_HARNESS=1 to run the live harness integration test")

    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env")

    if not _has_supported_api_key():
        pytest.skip(
            "Missing provider API key (OPENROUTER_API_KEY / CHUTES_API_KEY / MINIMAX_API_KEY)"
        )
    completed = subprocess.run(
        [sys.executable, "docs/harness/tool_call_types_harness.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )

    assert completed.returncode == 0, (
        "Harness failed\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}\n"
    )

    lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    expected_prefixes = (
        "agent_event_types=",
        "agent_event_class_types=",
        "assistant_stream_event_types=",
        "message_types=",
        "content_types=",
        "result_type=",
    )

    for prefix in expected_prefixes:
        assert any(line.startswith(prefix) for line in lines), (
            f"Missing output line prefix: {prefix}\nstdout:\n{completed.stdout}"
        )

    result_line = next(line for line in lines if line.startswith("result_type="))
    assert result_line == "result_type=AssistantMessage"
