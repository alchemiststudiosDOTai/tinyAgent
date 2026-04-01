# Rust Rewrite Docs

This directory is the current doc set for the Rust rewrite on `rust-rewrite`.

## Read In This Order

1. `docs/rust-runtime-types.md`
   Runtime-owned types and invariants in `rust/src/types.rs`.
2. `docs/rust-agent-alchemy-backend.md`
   How `Agent` connects to the typed alchemy backend.
3. `docs/rust-data-ingress-contracts.md`
   Where ingress is validated and how contract conformance is proved.
4. `docs/rust-real-agent.md`
   What the current agent already does end to end.

## Code Map

- `rust/src/lib.rs`
  Public crate exports.
- `rust/src/types.rs`
  Runtime message, event, tool, context, stream, and state types.
- `rust/src/agent.rs`
  Agent API, state reduction, run control, and listeners.
- `rust/src/agent_loop.rs`
  Turn loop, streaming reduction, context build, and continuation.
- `rust/src/agent_tool_execution.rs`
  Tool-call extraction, execution, update events, and tool result messages.
- `rust/src/alchemy_backend.rs`
  Typed runtime-to-alchemy conversions and live backend bridge.
- `rust/examples/minimax_agent_multiturn.rs`
  Real multi-turn, tool-calling example.

## Validation

```bash
cargo test --manifest-path rust/Cargo.toml
```

```bash
CARGO_HUSKY_DONT_INSTALL_HOOKS=1 cargo run --manifest-path rust/Cargo.toml --example minimax_agent_multiturn
```

The example command requires `MINIMAX_API_KEY`.
