#!/usr/bin/env bash
set -euo pipefail

[[ -n "${HOME:-}" && -f "$HOME/.cargo/env" ]] && . "$HOME/.cargo/env"

TAIL_LINES="${HARNESS_TAIL_LINES:-80}"
LOG_DIR="$(mktemp -d -t alchemy-harness-XXXXXX)"
KEEP_LOGS=0

cleanup() {
    if [[ "$KEEP_LOGS" -eq 0 ]]; then
        rm -rf "$LOG_DIR"
    fi
}
trap cleanup EXIT

run_step() {
    local step_name="$1"
    shift

    local log_file="${LOG_DIR}/${step_name// /_}.log"

    if "$@" >"$log_file" 2>&1; then
        printf '✓ %s\n' "$step_name"
        return 0
    fi

    KEEP_LOGS=1
    printf '✗ %s\n' "$step_name"
    printf '  command: %s\n' "$*"
    printf '  log: %s\n' "$log_file"
    printf '%s\n' "--- last ${TAIL_LINES} lines ---"
    tail -n "$TAIL_LINES" "$log_file" || true
    printf '%s\n' '--- end ---'
    exit 1
}

run_step "fmt" cargo fmt --all -- --check
run_step "clippy" cargo clippy --all-targets --all-features -- -D warnings
run_step "check" cargo check --all-targets --all-features
run_step "test" cargo test --all-features
run_step "complexity" make complexity
run_step "duplicates" make duplicates
run_step "dead-code" make dead-code
run_step "ast-rules" make ast-rules
run_step "large-files" make large-files

printf '✓ harness passed\n'
