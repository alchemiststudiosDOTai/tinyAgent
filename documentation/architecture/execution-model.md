# Execution Model

Async-first design with sync tool support.

## Why Async

Agents make HTTP calls to LLM APIs. These are I/O-bound operations with latency measured in seconds. Async enables:

- **Concurrent agents** without threading complexity
- **Non-blocking waits** during API calls
- **Integration** with async web frameworks (FastAPI, etc.)

For single-agent scripts, async adds ceremony (`asyncio.run()`). That's the tradeoff.

## Running Agents

### Async (native)

```python
import asyncio
from tinyagent import ReactAgent

agent = ReactAgent(tools=[...])
result = await agent.run("your prompt")

# or from sync context
result = asyncio.run(agent.run("your prompt"))
```

### Sync

```python
from tinyagent import ReactAgent

agent = ReactAgent(tools=[...])
result = agent.run_sync("your prompt")
```

No `asyncio` import needed. Internally calls `asyncio.run(self.run(...))`.

## Tool Execution

Tools can be sync or async. The agent handles both.

| Tool Type | Detection | Execution |
|-----------|-----------|-----------|
| Async | `inspect.iscoroutinefunction(fn)` | `await fn(...)` |
| Sync | Default | `asyncio.to_thread(fn, ...)` |

### Async Tool

```python
@tool
async def fetch_url(url: str) -> str:
    """Fetch a URL."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.text
```

### Sync Tool

```python
@tool
def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))
```

Sync tools are offloaded to a thread pool via `asyncio.to_thread()`. This prevents blocking the event loop but adds minor overhead.

## When to Use Async Tools

Use async when your tool does I/O:
- HTTP requests
- Database queries
- File operations (with aiofiles)
- WebSocket communication

Use sync when:
- Pure computation (math, string manipulation)
- Calling sync-only libraries (numpy, pandas)
- CPU-bound work

## Implementation Details

Tool execution lives in `tinyagent/core/registry.py`:

```python
async def run(self, payload: Dict[str, Any]) -> str:
    bound = self.signature.bind(**payload)
    if self.is_async:
        result = await self.fn(*bound.args, **bound.kwargs)
    else:
        result = await asyncio.to_thread(self.fn, *bound.args, **bound.kwargs)
    return str(result)
```

The `is_async` flag is set at decoration time by inspecting the function.

## Data Flow

```
agent.run(prompt)
       |
       v
  +----------+
  | LLM call |  <-- async HTTP
  +----------+
       |
       v
  +------------+
  | tool.run() |
  +------------+
       |
       +---> async tool: await fn()
       |
       +---> sync tool: asyncio.to_thread(fn)
       |
       v
  +-------------+
  | observation |
  +-------------+
       |
       v
  (loop or return)
```

## Best Practices

1. **Prefer async for I/O-bound tools** - Avoids thread pool overhead
2. **Use sync for CPU-bound work** - Thread pool keeps event loop responsive
3. **Don't mix sync HTTP in async tools** - Use `httpx.AsyncClient`, not `requests`
4. **Keep tools fast** - Long-running tools block the agent loop

## Common Patterns

### Wrapping a sync library

```python
@tool
def analyze_data(data: str) -> str:
    """Analyze data with pandas."""
    import pandas as pd
    df = pd.read_json(data)
    return df.describe().to_string()
```

Runs in thread pool automatically. No changes needed.

### Async HTTP tool

```python
@tool
async def search_web(query: str) -> str:
    """Search the web."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.search.com?q={query}")
        return resp.json()["results"]
```

Runs on event loop. Efficient for high-concurrency scenarios.
