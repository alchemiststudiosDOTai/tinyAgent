# Providers

LLM provider implementations that satisfy the `StreamFn` protocol.

## OpenRouter Provider

```python
from tinyagent import OpenRouterModel, stream_openrouter
```

OpenRouter provides unified access to multiple LLM providers through a single API.

For detailed guidance on targeting non-OpenRouter backends with `base_url`, see:
[`openai-compatible-endpoints.md`](openai-compatible-endpoints.md).

For the unified token/usage contract shared by Python and Rust paths, see:
[`usage-semantics.md`](usage-semantics.md).

### OpenRouterModel
```python
@dataclass
class OpenRouterModel(Model):
    provider: str = "openrouter"
    id: str = "anthropic/claude-3.5-sonnet"
    api: str = "openrouter"

    # OpenAI-compatible /chat/completions endpoint
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"

    # OpenRouter-specific routing controls (optional)
    openrouter_provider: dict[str, object] | None = None
    openrouter_route: str | None = None
```

Model configuration for OpenRouter (or any OpenAI-compatible endpoint via `base_url`).

**Common Model IDs**:
- `anthropic/claude-3.5-sonnet`
- `anthropic/claude-3.5-haiku`
- `anthropic/claude-3-opus`
- `openai/gpt-4o`
- `openai/gpt-4o-mini`
- `google/gemini-pro-1.5`

### stream_openrouter
```python
async def stream_openrouter(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> OpenRouterStreamResponse
```

Stream a response from OpenRouter.

**API Key Resolution**:
1. `options["api_key"]`
2. `OPENROUTER_API_KEY` environment variable

**Raises**: `ValueError` if no API key found

**Features**:
- SSE streaming via httpx
- Text delta streaming
- Tool call extraction (streaming JSON parsing)
- Automatic message format conversion (OpenAI-compatible)

**Example**:
```python
from tinyagent import Agent, AgentOptions, OpenRouterModel, stream_openrouter

agent = Agent(AgentOptions(stream_fn=stream_openrouter))
agent.set_model(OpenRouterModel(id="anthropic/claude-3.5-sonnet"))
agent.set_system_prompt("You are a helpful assistant.")

response = await agent.prompt_text("What is the meaning of life?")
```

**Custom OpenAI-compatible endpoint**:
```python
agent.set_model(
    OpenRouterModel(
        id="gpt-4o-mini",
        base_url="https://api.openai.com/v1/chat/completions",
    )
)
```

### OpenRouterStreamResponse
```python
class OpenRouterStreamResponse:
    async def result(self) -> AssistantMessage
    def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]
```

Response object that implements the `StreamResponse` protocol.

## Alchemy Provider

```python
from tinyagent.alchemy_provider import (
    OpenAICompatModel,
    stream_alchemy_openai_completions,
    stream_alchemy_openrouter,
)
```

Rust-based provider using the `alchemy-llm` crate via PyO3 bindings.

### OpenAICompatModel
```python
ReasoningEffort = Literal["minimal", "low", "medium", "high", "xhigh"]
ReasoningMode = bool | ReasoningEffort

@dataclass
class OpenAICompatModel(Model):
    provider: str = "openrouter"
    id: str = "moonshotai/kimi-k2.5"
    api: str = "openai-completions"

    # Additional fields for Rust binding
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    name: str | None = None
    headers: dict[str, str] | None = None
    context_window: int = 128_000
    max_tokens: int = 4096
    reasoning: ReasoningMode = False
```

Model configuration for the Rust binding (`tinyagent._alchemy`).

**Routing fields (`provider`, `api`, `base_url`)**:
- `provider`: Which backend family you are targeting (`openrouter`, `openai`, `minimax`, `minimax-cn`, or custom label)
- `api`: Which alchemy unified API to dispatch to (currently `openai-completions` or `minimax-completions`)
- `base_url`: Concrete endpoint URL used for the request

**API inference rules** (when using `stream_alchemy_openai_completions` / `stream_alchemy_openrouter`):
- explicit `model.api` wins
- if `model.api` is blank:
  - `provider in {"minimax", "minimax-cn"}` => `api = "minimax-completions"`
  - otherwise => `api = "openai-completions"`
- legacy aliases are normalized:
  - `api="openrouter"` / `api="openai"` => `openai-completions`
  - `api="minimax"` => `minimax-completions`

**Reasoning Mode**:
- `False` (default): No reasoning
- `True`: Enable reasoning (provider default effort)
- `"minimal"`, `"low"`, `"medium"`, `"high"`, `"xhigh"`: Specific effort level

### stream_alchemy_openai_completions
```python
async def stream_alchemy_openai_completions(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> AlchemyStreamResponse
```

Stream using the Rust alchemy-llm implementation.

Dispatch is selected from `model.api` (or inferred from `model.provider`) and routed
through the unified alchemy layer (`openai-completions` / `minimax-completions`).

### stream_alchemy_openrouter
```python
async def stream_alchemy_openrouter(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> AlchemyStreamResponse
```

Convenience alias for Rust-backed OpenRouter/OpenAI-compatible streaming.
Works with `OpenRouterModel` (including `base_url` overrides).

**API key resolution**:
1. `options["api_key"]`
2. `OPENAI_API_KEY` when `provider == "openai"`
3. `OPENROUTER_API_KEY` when `provider == "openrouter"`
4. `MINIMAX_API_KEY` when `provider == "minimax"`
5. `MINIMAX_CN_API_KEY` when `provider == "minimax-cn"`

**Live-verified compatibility**:
- OpenRouter default endpoint via Rust binding
- Chutes endpoint (`https://llm.chutes.ai/v1/chat/completions`) via Rust binding with `OpenRouterModel(base_url=...)`

**Rust + Chutes example**:
```python
from tinyagent import OpenRouterModel
from tinyagent.alchemy_provider import stream_alchemy_openrouter

model = OpenRouterModel(
    id="Qwen/Qwen3-32B",
    base_url="https://llm.chutes.ai/v1/chat/completions",
)

response = await stream_alchemy_openrouter(
    model,
    context,
    {"api_key": chutes_api_key},
)
```

**MiniMax global example**:
```python
from tinyagent.alchemy_provider import OpenAICompatModel, stream_alchemy_openai_completions

model = OpenAICompatModel(
    provider="minimax",
    api="minimax-completions",  # optional if provider is minimax
    id="MiniMax-M2.5",
    base_url="https://api.minimax.io/v1/chat/completions",
)

response = await stream_alchemy_openai_completions(
    model,
    context,
    {},  # resolves MINIMAX_API_KEY when api_key is omitted
)
```

**MiniMax CN example**:
```python
model = OpenAICompatModel(
    provider="minimax-cn",
    api="minimax-completions",  # optional if provider is minimax-cn
    id="MiniMax-M2.5",
    base_url="https://api.minimax.chat/v1/chat/completions",
)

response = await stream_alchemy_openai_completions(
    model,
    context,
    {},  # resolves MINIMAX_CN_API_KEY when api_key is omitted
)
```

**Requirements**:
```bash
pip install maturin
maturin develop
```

**Limitations**:
- Rust binding currently dispatches only `openai-completions` and `minimax-completions`
- Image blocks not supported
- Uses blocking `next_event()` in thread pool (more overhead than native async)

**When to Use**:
- High-throughput scenarios where Rust performance matters
- Consistent behavior with Rust-based services

### Reasoning Responses

When `reasoning=True` or a reasoning effort level is set, models that support reasoning
(e.g., `deepseek/deepseek-r1`) return responses with separate content blocks:

```python
{
    "content": [
        {"type": "thinking", "thinking": "Let me reason step by step..."},
        {"type": "text", "text": "The answer is 5."}
    ]
}
```

**Content Block Types**:
- `ThinkingContent`: `type: "thinking"`, `thinking: str`
- `TextContent`: `type: "text"`, `text: str`

**Filtering Content Blocks**:
```python
from typing import TypeGuard
from tinyagent.agent_types import (
    AssistantContent,
    AssistantMessage,
    TextContent,
    ThinkingContent,
)

def is_thinking_content(block: AssistantContent | None) -> TypeGuard[ThinkingContent]:
    return block is not None and block.get("type") == "thinking"

def is_text_content(block: AssistantContent | None) -> TypeGuard[TextContent]:
    return block is not None and block.get("type") == "text"

# Usage
content = message.get("content") or []
thinking_blocks = [b for b in content if is_thinking_content(b)]
text_blocks = [b for b in content if is_text_content(b)]
```

**Streaming Events**:
- `thinking_start`, `thinking_delta`, `thinking_end`: Reasoning content
- `text_start`, `text_delta`, `text_end`: Final answer content

See `examples/example_reasoning.py` for a complete example.

## Proxy Provider

```python
from tinyagent import (
    ProxyStreamOptions,
    ProxyStreamResponse,
    stream_proxy,
    create_proxy_stream,
    parse_streaming_json,
)
```

Client for apps that route LLM calls through a proxy server.

**Use Case**: Web applications where the server manages:
- API keys
- Provider selection
- Request logging/auditing
- Rate limiting

### ProxyStreamOptions
```python
@dataclass
class ProxyStreamOptions:
    auth_token: str          # Authentication with proxy
    proxy_url: str           # Base URL of proxy server
    temperature: float | None = None
    max_tokens: int | None = None
    reasoning: JsonValue | None = None
    signal: Callable[[], bool] | None = None  # Cancellation check
```

### stream_proxy
```python
async def stream_proxy(
    model: Model,
    context: Context,
    options: ProxyStreamOptions,
) -> ProxyStreamResponse
```

Stream function compatible with the agent loop.

Posts to `{proxy_url}/api/stream` with SSE response handling.

### create_proxy_stream
```python
async def create_proxy_stream(
    model: Model,
    context: Context,
    auth_token: str,
    proxy_url: str,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning: JsonValue | None = None,
    signal: Callable[[], bool] | None = None,
) -> ProxyStreamResponse
```

Convenience helper that creates options and calls `stream_proxy`.

### ProxyStreamResponse
```python
class ProxyStreamResponse:
    async def result(self) -> AssistantMessage
    def __aiter__(self) -> AsyncIterator[AssistantMessageEvent]
```

Implements `StreamResponse` protocol for proxy SSE streams.

### parse_streaming_json
```python
def parse_streaming_json(json_str: str) -> JsonObject | None
```

Parse partial JSON from a streaming response.

Handles incomplete JSON by counting braces and appending closing braces.

**Example**:
```python
# Partial JSON from streaming tool arguments
partial = '{"query": "hello'  # Missing closing quote and brace
result = parse_streaming_json(partial)
# Returns: {"query": "hello"} or None if unparseable
```

## Creating Custom Providers

To implement a new provider, create a function matching `StreamFn`:

```python
from tinyagent import StreamResponse, Model, Context, SimpleStreamOptions

async def my_provider(
    model: Model,
    context: Context,
    options: SimpleStreamOptions,
) -> StreamResponse:
    # 1. Convert messages to provider format
    # 2. Make streaming request
    # 3. Yield AssistantMessageEvent objects
    # 4. Return final AssistantMessage
    ...
```

### StreamResponse Protocol

Your response object must implement:

```python
class MyStreamResponse:
    async def result(self) -> AssistantMessage:
        """Return the final complete message."""
        ...

    def __aiter__(self):
        """Return async iterator."""
        ...

    async def __anext__(self) -> AssistantMessageEvent:
        """Yield next event or raise StopAsyncIteration."""
        ...
```

### AssistantMessageEvent Types

Your provider should emit these event types:

- `start`: Streaming begins
- `text_start`, `text_delta`, `text_end`: Text content
- `thinking_start`, `thinking_delta`, `thinking_end`: Reasoning content
- `tool_call_start`, `tool_call_delta`, `tool_call_end`: Tool calls
- `done`: Streaming complete
- `error`: Error occurred

Each event should include `partial`: the current `AssistantMessage` being built.
