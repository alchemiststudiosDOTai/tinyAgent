# tinyagent-rs

`tinyagent-rs` is a standalone Rust rewrite of the Python `tinyAgent` runtime.

The crate keeps the public agent semantics in `tinyagent-rs`, uses `alchemy-rs`
for provider dispatch and assistant streaming, and keeps `looper-rs` usage in a
private support layer.

## Status

Implemented in this crate:

- `Agent::prompt`, `prompt_text`, `stream`, `stream_text`, `continue_`
- steering and follow-up queues
- abort and wait-for-idle
- parallel tool execution with ordered replay
- direct `alchemy-rs` streaming adapter
- offline parity tests

## Quick Start

```rust
use tinyagent_rs::{Agent, AgentOptions, Model};

#[tokio::main]
async fn main() -> tinyagent_rs::Result<()> {
    let agent = Agent::new(AgentOptions {
        model: Some(Model {
            provider: "minimax".to_string(),
            id: "MiniMax-M2.5".to_string(),
            api: "minimax-completions".to_string(),
            ..Model::default()
        }),
        ..AgentOptions::default()
    });

    let response = agent.prompt("Reply with one sentence.").await?;
    println!("{}", tinyagent_rs::extract_text(&tinyagent_rs::AgentMessage::Assistant(response)));
    Ok(())
}
```

## Examples

- `cargo run --manifest-path tinyagent-rs/Cargo.toml --example prompt`
- `cargo run --manifest-path tinyagent-rs/Cargo.toml --example stream`
- `cargo run --manifest-path tinyagent-rs/Cargo.toml --example tools`
- `cargo run --manifest-path tinyagent-rs/Cargo.toml --example steer`

## Live Smoke Test

Copy `.env.example` to `.env` or otherwise export the provider key, then run:

```bash
RUN_LIVE_ALCHEMY_TESTS=1 cargo test --manifest-path tinyagent-rs/Cargo.toml live_minimax_smoke -- --ignored --nocapture
```

The first live smoke path targets the direct `alchemy-rs` MiniMax integration.
