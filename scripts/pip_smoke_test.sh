#!/usr/bin/env bash
# quick_test.sh – one‑shot "does the package work?" script
set -euo pipefail

msg(){ printf "\033[32m==>\033[0m %s\n" "$*"; }
err(){ printf "\033[31mERROR:\033[0m %s\n" "$*" >&2; exit 1; }

# ─── ensure build tool ───────────────────────────────────
python3 -m pip show build >/dev/null 2>&1 || {
  msg "Installing build ⏳"; python3 -m pip install -q build; }

# ─── build wheel if none exists ─────────────────────────
[[ -e dist/*.whl ]] || { msg "No wheel → python3 -m build"; python3 -m build >/dev/null; }

wheel=$(ls -t dist/*.whl | head -n1) || err "build failed"
msg "Using wheel: $wheel"

# ─── temp venv ──────────────────────────────────────────
tmp=$(mktemp -d); python3 -m venv "$tmp/venv"
source "$tmp/venv/bin/activate"
python3 -m pip install -q --upgrade pip "$wheel[rag]"

# ─── smoke checks ──────────────────────────────────────
msg "Import test"
python3 - <<'PY'
import tinyagent, sys
print(" tinyagent v", getattr(tinyagent, "__version__", "dev"))
PY

msg "CLI --help"
tinyagent --help >/dev/null && echo "  OK"

msg "Functional tool/agent test"
python3 - <<'PY'
from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent

@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

agent = tiny_agent(tools=[calculate_sum])
result = agent.run("calculate the sum of 5 and 3", expected_type=int)
assert result == 8, f"expected 8, got {result}"
print("  OK → sum = 8")
PY



msg "Running rag_smoke_test.py"
python3 tests/rag_smoke_test.py || err "rag_smoke_test.py failed"

msg "All smoke‑tests passed ✔︎"
deactivate; rm -rf "$tmp"
