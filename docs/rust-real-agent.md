# Real Agent Runtime

The current `Agent` in `rust/src/agent.rs` is a real runtime entrypoint, not a stub state holder.

It already owns:

- persistent `AgentState`
- listener subscription
- prompt construction
- stream consumption
- event reduction
- multi-turn continuation
- steering and follow-up queues
- tool registration
- abort signaling

The only provider assumption is the `StreamFn` backend interface.

## Public Runtime Surface

The main operator-facing methods are:

- `set_model(...)`
- `set_system_prompt(...)`
- `set_tools(...)`
- `set_stream_fn(...)`
- `prompt(...)`
- `prompt_text(...)`
- `continue_(...)`
- `subscribe(...)`
- `abort(...)`

This is enough to run a stateful agent against a real backend today.

## Run Lifecycle

### 1. Configuration

The caller wires:

- runtime `Model`
- system prompt
- runtime tools
- backend `StreamFn`

### 2. Prompt ingress

`prompt(...)` and `prompt_text(...)` normalize input into typed user messages through `build_input_messages(...)`.

### 3. Loop boot

`run_prompts(...)` or `continue_(...)` starts a run by:

- creating an abort signal
- building `AgentContext`
- building `AgentLoopConfig`
- starting `agent_loop(...)` or `agent_loop_continue(...)`

### 4. Stream reduction

`consume_stream(...)` reads `AgentEvent` values from the loop and applies them to `AgentState`.

The important state mutations are:

- `MessageStart` and `MessageUpdate` set `stream_message`
- `MessageEnd` appends the final message into state
- `ToolExecutionStart` inserts the tool-call id into `pending_tool_calls`
- `ToolExecutionEnd` removes the tool-call id from `pending_tool_calls`
- `TurnEnd` captures assistant error text when present
- `AgentEnd` clears streaming state

### 5. Final response

Once the stream closes cleanly, `Agent` returns the last assistant message from state.

If the stream fails, `Agent` records the error and appends a typed runtime assistant error message using `create_error_message(...)`.

## Queue Behavior

The runtime supports two queue types:

- steering queue
- follow-up queue

Each queue can run in:

- `QueueMode::All`
- `QueueMode::OneAtATime`

The loop drains queued steering messages first, then follow-up messages after the active turn finishes.

## Real Tool Execution

The real agent already integrates the tool runner.

If an assistant message contains tool-call content blocks:

1. the loop validates tool calls
2. the tool executor runs them concurrently
3. tool execution events are emitted
4. tool results are appended into runtime context
5. the loop continues with those tool results available to the model

So tool calls are not mocked. They are part of the current runtime path.

## Real Multi-Turn Example

`rust/examples/minimax_agent_multiturn.rs` is the current proof example for the real agent.

It does all of the following in one runnable program:

- constructs `AlchemyBackend::new(minimax_m2_7())`
- wires the backend into `AgentOptions`
- sets the runtime model from `backend.runtime_model()`
- registers two executable tools
- runs turn 1 with `prompt_text(...)`
- runs turn 2 with `prompt_text(...)`
- counts tool execution events through `subscribe(...)`
- asserts multi-turn arithmetic behavior

## What the Example Proves

The example proves the rewrite already has:

- a real runtime `Agent`
- a real typed backend connection
- real tool execution
- real multi-turn state
- real listener events

It is not a fake adapter and not a placeholder shell around the provider crate.

## Live Validation

When last validated on this branch, the example completed with:

```text
running turn 1...
turn_1=56088
running turn 2...
turn_2=56098
tool_call_count=2
message_count=8
```

Run it with:

```bash
CARGO_HUSKY_DONT_INSTALL_HOOKS=1 cargo run --manifest-path rust/Cargo.toml --example minimax_agent_multiturn
```

This command requires a valid `MINIMAX_API_KEY` in the environment.
