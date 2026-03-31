---
title: "python parity map research findings"
link: "python-parity-map-research"
type: research
ontological_relations:
  - relates_to: [[docs/ARCHITECTURE.md]]
  - relates_to: [[docs/api/README.md]]
tags: [research, python, parity, agent]
uuid: "153DE077-EEBF-4D0B-A575-18E7DAB2B97B"
created_at: "2026-03-31T02:03:35Z"
---

## Structure
- `tinyagent/agent.py` implements the high-level `Agent` wrapper and local state/event handling.
- `tinyagent/agent_loop.py` runs turn orchestration and the assistant/tool loop.
- `tinyagent/agent_tool_execution.py` validates tool-call arguments, executes tool calls concurrently, and emits tool events.
- `tinyagent/alchemy_provider.py` adapts `tinyagent._alchemy` Rust streams into the shared `StreamResponse` contract.
- `tinyagent/proxy.py` sends SSE requests to a proxy server and converts proxy events into `AssistantMessageEvent` objects.
- `tinyagent/proxy_event_handlers.py` mutates a shared partial `AssistantMessage` from proxy protocol events.
- `tinyagent/caching.py` annotates `UserMessage` text blocks with `cache_control` metadata and normalizes usage/cache counts.
- `tinyagent/agent_types.py` defines shared message/content/tool/context/model/event/state types and the `EventStream` primitive.

## Key Files
- `tinyagent/agent_types.py:18` defines `JsonPrimitive`, `JsonValue`, `JsonObject`.
- `tinyagent/agent_types.py:72` defines `ThinkingBudgets`; `tinyagent/agent_types.py:84` defines `ThinkingLevel`.
- `tinyagent/agent_types.py:95` defines `CacheControl`; `tinyagent/agent_types.py:101`, `:118`, `:127` define `TextContent`, `ThinkingContent`, `ToolCallContent`.
- `tinyagent/agent_types.py:142`, `:173`, `:187`, `:202` define `UserMessage`, `AssistantMessage`, `ToolResultMessage`, `CustomAgentMessage`.
- `tinyagent/agent_types.py:226` defines `AgentToolResult`; `tinyagent/agent_types.py:237` and `:246` define `Tool` and `AgentTool`.
- `tinyagent/agent_types.py:259` and `:268` define `Context` and `AgentContext`; `tinyagent/agent_types.py:277` defines `Model`; `tinyagent/agent_types.py:286` defines `SimpleStreamOptions`.
- `tinyagent/agent_types.py:298` defines `AssistantMessageEvent`; `tinyagent/agent_types.py:343` defines the `StreamResponse` protocol.
- `tinyagent/agent_types.py:358-478` defines `AgentEvent` dataclasses plus type-guard helpers.
- `tinyagent/agent_types.py:482` defines `AgentLoopConfig`; `tinyagent/agent_types.py:496` defines `AgentState`; `tinyagent/agent_types.py:518` defines `EventStream`.
- `tinyagent/agent.py:256` defines `AgentOptions`; `tinyagent/agent.py:272` defines `Agent`.
- `tinyagent/agent_loop.py:183` defines `stream_assistant_response`; `tinyagent/agent_loop.py:314` defines `run_loop`; `tinyagent/agent_loop.py:368` and `:410` define `agent_loop` and `agent_loop_continue`.
- `tinyagent/agent_tool_execution.py:29` defines `ToolExecutionResult`; `tinyagent/agent_tool_execution.py:164` defines `execute_tool_calls`.
- `tinyagent/alchemy_provider.py:140` defines `OpenAICompatModel`; `tinyagent/alchemy_provider.py:156` defines `AlchemyStreamResponse`; `tinyagent/alchemy_provider.py:269` defines `stream_alchemy_openai_completions`.
- `tinyagent/proxy.py:34` defines `ProxyStreamOptions`; `tinyagent/proxy.py:166` defines `ProxyStreamResponse`; `tinyagent/proxy.py:272` and `:280` define `stream_proxy` and `create_proxy_stream`.
- `tinyagent/proxy_event_handlers.py:324` defines `process_proxy_event`.
- `tinyagent/caching.py:62` defines `add_cache_breakpoints`.
- `tinyagent/__init__.py:6-58` re-exports the public package surface for `Agent`, loop functions, tool helpers, types, and proxy helpers.
- `tests/architecture/test_import_boundaries.py:30-42` defines the enforced layer order: `agent` -> `agent_loop|proxy` -> `agent_tool_execution|alchemy_provider|rust_binding_provider|proxy_event_handlers|caching` -> `agent_types`.

## Signatures
- `tinyagent/agent_types.py:212-218`
  `ConvertToLlmFn = Callable[[list[AgentMessage]], MaybeAwaitable[list[Message]]]`
  `TransformContextFn = Callable[[list[AgentMessage], asyncio.Event | None], Awaitable[list[AgentMessage]]]`
  `ApiKeyResolver = Callable[[str], MaybeAwaitable[str | None]]`
  `AgentMessageProvider = Callable[[], Awaitable[list[AgentMessage]]]`
- `tinyagent/agent_types.py:295`
  `StreamFn = Callable[[Model, Context, SimpleStreamOptions], Awaitable["StreamResponse"]]`
- `tinyagent/agent.py:427-431`
  `async def prompt(self, input_data: str | AgentMessage | list[AgentMessage], images: list[ImageContent] | None = None) -> AgentMessage`
- `tinyagent/agent.py:455-459`
  `async def prompt_text(self, input_data: str | AgentMessage | list[AgentMessage], images: list[ImageContent] | None = None) -> str`
- `tinyagent/agent.py:462-466`
  `def stream(self, input_data: str | AgentMessage | list[AgentMessage], images: list[ImageContent] | None = None) -> AsyncIterator[AgentEvent]`
- `tinyagent/agent.py:510-514`
  `def stream_text(self, input_data: str | AgentMessage | list[AgentMessage], images: list[ImageContent] | None = None) -> AsyncIterator[str]`
- `tinyagent/agent.py:542`
  `async def continue_(self) -> AgentMessage`
- `tinyagent/agent_loop.py:183-189`
  `async def stream_assistant_response(context: AgentContext, config: AgentLoopConfig, signal: asyncio.Event | None, stream: EventStream, stream_fn: StreamFn | None = None) -> AssistantMessage`
- `tinyagent/agent_loop.py:314-321`
  `async def run_loop(current_context: AgentContext, new_messages: list[AgentMessage], config: AgentLoopConfig, signal: asyncio.Event | None, stream: EventStream, stream_fn: StreamFn | None = None) -> None`
- `tinyagent/agent_loop.py:368-374`
  `def agent_loop(prompts: list[AgentMessage], context: AgentContext, config: AgentLoopConfig, signal: asyncio.Event | None = None, stream_fn: StreamFn | None = None) -> EventStream`
- `tinyagent/agent_loop.py:410-415`
  `def agent_loop_continue(context: AgentContext, config: AgentLoopConfig, signal: asyncio.Event | None = None, stream_fn: StreamFn | None = None) -> EventStream`
- `tinyagent/agent_tool_execution.py:164-170`
  `async def execute_tool_calls(tools: list[AgentTool] | None, assistant_message: AssistantMessage, signal: asyncio.Event | None, stream: EventStream, get_steering_messages: Callable[[], Awaitable[list[AgentMessage]]] | None = None) -> ToolExecutionResult`
- `tinyagent/alchemy_provider.py:269-273`
  `async def stream_alchemy_openai_completions(model: Model, context: Context, options: SimpleStreamOptions) -> AlchemyStreamResponse`
- `tinyagent/proxy.py:272-274`
  `async def stream_proxy(model: Model, context: Context, options: ProxyStreamOptions) -> ProxyStreamResponse`
- `tinyagent/proxy.py:280-290`
  `async def create_proxy_stream(model: Model, context: Context, auth_token: str, proxy_url: str, *, temperature: float | None = None, max_tokens: int | None = None, reasoning: JsonValue | None = None, signal: Callable[[], bool] | None = None) -> ProxyStreamResponse`

## Dependencies
- `tinyagent/agent.py:10-40` imports `agent_loop`, `agent_types`, and `caching`.
- `tinyagent/agent_loop.py:13-37` imports `execute_tool_calls` from `agent_tool_execution` and shared types from `agent_types`.
- `tinyagent/agent_tool_execution.py:11-26`, `tinyagent/alchemy_provider.py:22-31`, `tinyagent/caching.py:9-17`, `tinyagent/proxy_event_handlers.py:9-20` import only `agent_types`.
- `tinyagent/proxy.py:19-30` imports `agent_types` and `process_proxy_event` from `proxy_event_handlers`.

## Data Flow
- High-level agent entry:
  `Agent.prompt()` normalizes input via `_build_input_messages()` and delegates to `_run_loop()` (`tinyagent/agent.py:400-419`, `:427-453`).
- Agent run setup:
  `_setup_run_state()` creates `_running_prompt`, `_abort_event`, and sets `AgentState.is_streaming` (`tinyagent/agent.py:601-607`).
  `_build_loop_context_and_config()` copies current `AgentState` into `AgentContext` and builds `AgentLoopConfig` from callbacks and queues (`tinyagent/agent.py:609-625`).
- Loop startup:
  `_run_loop()` selects `agent_loop()` when new messages are supplied or `agent_loop_continue()` otherwise, then consumes the returned `EventStream` and feeds each event into `_handle_agent_event()` plus local listeners (`tinyagent/agent.py:566-599`).
- State mutation from events:
  `_on_message_start_or_update()` sets `state.stream_message` (`tinyagent/agent.py:43-53`).
  `_on_message_end()` appends completed messages (`tinyagent/agent.py:55-67`).
  `_on_tool_execution_start()` and `_on_tool_execution_end()` update `state.pending_tool_calls` (`tinyagent/agent.py:69-98`).
  `_on_turn_end()` copies assistant `error_message` into `state.error` (`tinyagent/agent.py:100-113`).
  `_on_agent_end()` clears streaming state (`tinyagent/agent.py:115-123`).
- Context transformation boundary:
  `_build_llm_context()` optionally applies `transform_context`, then `convert_to_llm`, and returns `Context(system_prompt, llm_messages, tools)` (`tinyagent/agent_loop.py:87-105`).
- Stream boundary:
  `stream_assistant_response()` builds `SimpleStreamOptions`, calls the selected `stream_fn`, iterates provider events, and routes them through handlers created by `_create_stream_handlers()` (`tinyagent/agent_loop.py:183-220`).
  `handle_start()` appends the partial assistant message to `context.messages` and emits `MessageStartEvent` (`tinyagent/agent_loop.py:137-145`).
  update handlers replace the last context message with the new partial and emit `MessageUpdateEvent` (`tinyagent/agent_loop.py:147-159`).
  finish handlers call `response.result()`, replace or append the final assistant message, and emit `MessageEndEvent` (`tinyagent/agent_loop.py:161-170`).
- Turn processing:
  `_process_turn()` emits queued steering/follow-up messages via `_emit_pending_messages()`, requests an assistant response, then branches on `AssistantMessage.stop_reason` (`tinyagent/agent_loop.py:231-311`).
  For `stop_reason in ("error", "aborted")`, it emits `TurnEndEvent`, `AgentEndEvent`, and ends the stream (`tinyagent/agent_loop.py:274-284`).
  Otherwise it calls `execute_tool_calls()`, appends `ToolResultMessage` objects to `current_context.messages` and `new_messages`, emits `TurnEndEvent`, and computes the next pending message batch from steering or follow-up queues (`tinyagent/agent_loop.py:286-311`).
- Outer/inner loop control:
  `run_loop()` fetches initial steering messages, iterates turns while tool results or pending messages exist, then checks `get_follow_up_messages()` before ending with `AgentEndEvent` and `stream.end(new_messages)` (`tinyagent/agent_loop.py:324-365`).

## Tool Execution
- `execute_tool_calls()` extracts `ToolCallContent` blocks from the assistant message (`tinyagent/agent_tool_execution.py:54-59`, `:171-173`).
- It emits `ToolExecutionStartEvent` for every tool call before execution begins (`tinyagent/agent_tool_execution.py:175-184`).
- `_find_tool()` matches tool definitions by `tool.name` (`tinyagent/agent_tool_execution.py:62-68`).
- `_execute_single_tool()` normalizes arguments with `validate_tool_arguments()`, invokes `tool.execute(tool_call_id, validated_args, signal, on_update)`, emits `ToolExecutionUpdateEvent` from the `on_update` callback, and converts missing-tool / missing-execute / cancellation / exception cases into `AgentToolResult` text payloads (`tinyagent/agent_tool_execution.py:34-52`, `:82-147`).
- `execute_tool_calls()` runs all tool invocations concurrently via `asyncio.gather(...)`, then emits `ToolExecutionEndEvent`, converts each result into `ToolResultMessage`, and emits `MessageStartEvent` plus `MessageEndEvent` for each tool result (`tinyagent/agent_tool_execution.py:185-218`).
- After all tool executions finish, it optionally fetches one batch of steering messages and returns them alongside `tool_results` in `ToolExecutionResult` (`tinyagent/agent_tool_execution.py:211-218`).

## Alchemy Binding Path
- `_get_alchemy_module()` lazily imports `_alchemy` or `tinyagent._alchemy`, caching the resolved module in `_ALCHEMY_MODULE` (`tinyagent/alchemy_provider.py:111-137`).
- `OpenAICompatModel` extends `Model` with `base_url`, `name`, `headers`, `context_window`, `max_tokens`, and `reasoning` (`tinyagent/alchemy_provider.py:140-154`).
- `AlchemyStreamResponse.result()` calls `self._handle.result()` in a worker thread and validates the returned assistant message plus required `usage` keys (`tinyagent/alchemy_provider.py:163-174`, `:71-108`).
- `AlchemyStreamResponse.__anext__()` calls `self._handle.next_event()` in a worker thread and converts dict payloads to `AssistantMessageEvent` models (`tinyagent/alchemy_provider.py:179-188`).
- `stream_alchemy_openai_completions()` resolves provider, base URL, API, API key, and optional `OpenAICompatModel` fields, serializes `Context.messages` with `dump_model_dumpable()`, converts tools to simple dicts, calls `openai_completions_stream(model_dict, context_dict, options_dict)`, and wraps the handle in `AlchemyStreamResponse` (`tinyagent/alchemy_provider.py:190-325`).

## Proxy Path
- `ProxyStreamOptions` carries `auth_token`, `proxy_url`, optional `temperature`, `max_tokens`, `reasoning`, and an optional cancellation callback (`tinyagent/proxy.py:33-42`).
- `ProxyStreamResponse` creates a background task in `__init__()` and stores a mutable partial `AssistantMessage` seeded by `_create_initial_partial()` (`tinyagent/proxy.py:45-56`, `:169-179`).
- `_build_proxy_request_body()` serializes model/context and maps `max_tokens` to on-wire `maxTokens` (`tinyagent/proxy.py:101-115`).
- `_run_success()` POSTs to `{proxy_url}/api/stream` with bearer auth, then passes each SSE `data:` object through `process_proxy_event(proxy_event, self._partial)` (`tinyagent/proxy.py:224-249`, `:214-223`).
- `_queue_event()` stores `done`/`error` terminal events as `_final` and pushes each `AssistantMessageEvent` into an internal queue (`tinyagent/proxy.py:198-213`).
- `_run_error()` mutates the shared partial with `stop_reason` and `error_message`, then emits an `AssistantMessageEvent(type="error", error=self._partial)` (`tinyagent/proxy.py:250-261`).
- `stream_proxy()` returns a `ProxyStreamResponse`; `create_proxy_stream()` builds `ProxyStreamOptions` and delegates to `stream_proxy()` (`tinyagent/proxy.py:272-301`).

## Proxy Event Mutation Rules
- `process_proxy_event()` dispatches on `proxy_event["type"]` via `_PROXY_EVENT_HANDLERS` (`tinyagent/proxy_event_handlers.py:307-335`).
- `text_start` / `thinking_start` allocate a content slot in `partial.content` and install a `TextContent` or `ThinkingContent` placeholder (`tinyagent/proxy_event_handlers.py:93-108`).
- `text_delta` / `thinking_delta` append incoming `delta` strings directly onto the matching content block (`tinyagent/proxy_event_handlers.py:110-138`).
- `text_end` / `thinking_end` write `contentSignature` into `text_signature` or `thinking_signature` (`tinyagent/proxy_event_handlers.py:140-168`).
- `toolcall_start` creates a `ToolCallContent(id, name, arguments={}, partial_json="")` (`tinyagent/proxy_event_handlers.py:201-225`).
- `toolcall_delta` appends raw JSON fragments into `partial_json`, reparses with `parse_streaming_json()`, and updates `ToolCallContent.arguments` incrementally (`tinyagent/proxy_event_handlers.py:227-252`).
- `toolcall_end` clears `partial_json` and emits the final `tool_call` block (`tinyagent/proxy_event_handlers.py:254-268`).
- `done` and `error` write `stop_reason`, optional `usage`, and optional `error_message` onto the shared partial, then emit terminal `AssistantMessageEvent` objects (`tinyagent/proxy_event_handlers.py:271-297`).

## Caching Path
- `_build_transform_context()` composes `add_cache_breakpoints()` ahead of any user-supplied transform when `AgentOptions.enable_prompt_caching` is true (`tinyagent/agent.py:236-253`).
- `add_cache_breakpoints()` returns `_annotate_user_messages(messages)` and ignores the optional `signal` argument (`tinyagent/caching.py:62-77`).
- `_annotate_user_messages()` deep-copies each `UserMessage` whose last content block is `TextContent`, then writes `cache_control=CacheControl(type="ephemeral")` on that last block (`tinyagent/caching.py:22-59`).
- `_context_has_cache_control()`, `_convert_user_message()`, and `_build_usage_dict()` provide helpers for detecting structured cache-control blocks and normalizing provider usage/cache fields (`tinyagent/caching.py:88-181`).

## Public Surface And Stored State
- `Agent` exposes mutable state mutators for system prompt, model, thinking level, tools, messages, steering mode, and follow-up mode (`tinyagent/agent.py:329-381`).
- `Agent` stores `session_id` and `thinking_budgets` as instance properties with getters/setters (`tinyagent/agent.py:299-317`).
- `AgentState` stores `system_prompt`, `model`, `thinking_level`, `tools`, `messages`, `is_streaming`, `stream_message`, `pending_tool_calls`, and `error` (`tinyagent/agent_types.py:496-507`).
