# tinyagent-rs

`tinyagent-rs` is a standalone Rust rewrite of the Python `tinyAgent` agent layer.

It keeps the public agent semantics in this crate, uses `alchemy-rs` for provider
streaming, and reuses `looper-rs` for private support adapters where that reduces
duplication.

The crate is developed inside the `tinyAgent` repository as a sibling to the local
`alchemy-rs` and `looper-rs` checkouts used during implementation.
