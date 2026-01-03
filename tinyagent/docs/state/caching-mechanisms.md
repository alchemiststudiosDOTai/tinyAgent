---
title: Caching Mechanisms
path: .
type: directory
depth: 0
description: Token counting, result memoization, and caching patterns analysis
seams: [ExecutionLimits.truncate_output(), max_tokens, no built-in caching]
---

# Caching Mechanisms

## Overview

tinyAgent has **no explicit caching or memoization** implemented. Token counting is delegated to LLM providers, and result caching is not built-in. This document analyzes the current state and potential improvements.

## Current State

### 1. Token Counting

**Status**: No custom token counting implementation.

**Where it's handled**:
- **LLM Provider APIs**: Token counting done by OpenAI, Anthropic, etc.
- **max_tokens parameter**: Limit on response size (not caching)

**Example**:
```python
# In ReactAgent (agents/react.py)
max_tokens: int = 4096  # Limits response size, doesn't count tokens

# Passed to LLM API
response = llm.generate(messages, max_tokens=self.max_tokens)
```

**Limitations**:
- No visibility into actual token usage
- Can't implement token-aware pruning
- No feedback on token consumption
- Relies on provider's token counting

**What's Missing**:
```python
# Not implemented
def count_tokens(messages: list[dict]) -> int:
    """Count tokens using tiktoken or similar."""
    pass

def estimate_tokens(text: str) -> int:
    """Estimate token count for text."""
    pass
```

### 2. Result Memoization

**Status**: No memoization of tool results or LLM responses.

**Search Results**:
```bash
$ grep -r "cache" --include="*.py" .
# No results found
```

**Implications**:
- Repeated computations execute every time
- No reuse of previous tool results
- No caching of LLM responses
- Redundant API calls possible

**Example of What Could Be Cached**:
```python
# Currently executes every time
file_content = read_file("/path/to/file.txt")  # Executes repeatedly

# Could be memoized
@memoize
def read_file(path: str) -> str:
    # Only reads once per path
    pass
```

### 3. Scratchpad State

**Location**: `memory/scratchpad.py`

**Status**: Simple in-memory key-value store.

**Mechanism**:
```python
@dataclass
class AgentMemory:
    variables: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    failed_approaches: list[str] = field(default_factory=list)
```

**Is this caching?**
- **Not exactly**: It's working memory, not a cache
- **Purpose**: Store intermediate results for reasoning
- **Lifetime**: Exists only during single agent run
- **Persistence**: None (cleared after run)

**Usage Pattern**:
```python
# Store computed value
memory.store("file_count", len(files))

# Retrieve later
count = memory.recall("file_count")

# This is state management, not caching
```

**Key Differences**:
- **Caching**: Transparent optimization with invalidation
- **Scratchpad**: Explicit state management for reasoning

### 4. Step History Tracking

**Location**: `memory/manager.py`, `memory/steps.py`

**Status**: Conversation history stored in memory.

**Mechanism**:
```python
@dataclass
class MemoryManager:
    steps: list[Step] = field(default_factory=list)
```

**Is this caching?**
- **Not exactly**: It's conversation history
- **Purpose**: Maintain context for LLM
- **Lifetime**: Exists during agent run
- **Persistence**: None (cleared after run)

**Token Management**:
- **Pruning strategies**: Reduce history size
- **Not caching**: Removing old steps, not caching results

## Execution Limits (Output Truncation)

**Location**: `limits/boundaries.py`

**Purpose**: Prevent excessive output size from tool execution.

### Implementation

```python
@dataclass
class ExecutionLimits:
    max_output_bytes: int = 100_000  # 100KB default

    def truncate_output(self, output: str) -> tuple[str, bool]:
        if len(output.encode('utf-8')) > self.max_output_bytes:
            truncated = output[:self.max_output_bytes] + "\n[OUTPUT TRUNCATED]"
            return truncated, True
        return output, False
```

### Usage

**In TinyCodeAgent**:
```python
# In _handle_final_result
truncated_output, was_truncated = self.limits.truncate_output(raw_output)

# In LocalExecutor
truncated, _ = limits.truncate_output(output)
```

### Behavior

1. **Check size**: Count UTF-8 bytes
2. **Truncate if needed**: Cut off at limit
3. **Add marker**: Append `[OUTPUT TRUNCATED]`
4. **Return status**: Indicate whether truncation occurred

### Is this caching?

**No**: It's limiting output size, not caching.

**Relationship to caching**:
- Prevents memory bloat
- Reduces token usage
- Complements pruning strategies

## Why No Caching?

### Design Philosophy

1. **Simplicity**: Cache invalidation is complex
2. **Transparency**: Explicit state management preferred
3. **Determinism**: No hidden cache hits/misses
4. **Flexibility**: Agent controls what to store

### Use Case Considerations

**When caching helps**:
- Repeated file reads
- Expensive API calls
- Repeated computations
- Idempotent operations

**When caching doesn't help**:
- Unique operations
- Stateful operations
- Real-time data
- Side effects

## Potential Caching Strategies

### 1. Tool Result Caching

**Goal**: Cache results from expensive tools.

```python
from functools import lru_cache
import hashlib

class CachedToolExecutor:
    def __init__(self):
        self._cache: dict[str, Any] = {}

    def _cache_key(self, tool_name: str, args: dict) -> str:
        # Create deterministic cache key
        key_data = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def execute(self, tool_name: str, args: dict) -> Any:
        key = self._cache_key(tool_name, args)

        if key in self._cache:
            return self._cache[key]

        result = execute_tool(tool_name, args)
        self._cache[key] = result
        return result

    def invalidate(self, tool_name: str | None = None) -> None:
        if tool_name:
            # Invalidate all entries for this tool
            keys_to_remove = [k for k in self._cache
                            if k.startswith(tool_name)]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            # Clear all cache
            self._cache.clear()
```

**Considerations**:
- Cache invalidation strategy
- Memory vs speed tradeoff
- Deterministic serialization required
- Tool must be pure/idempotent

### 2. LLM Response Caching

**Goal**: Cache responses for repeated prompts.

```python
class LLMCache:
    def __init__(self, cache_file: str | None = None):
        self._cache: dict[str, str] = {}
        self._cache_file = cache_file
        self._load_cache()

    def _cache_key(self, messages: list[dict]) -> str:
        # Normalize messages for caching
        normalized = json.dumps(messages, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, messages: list[dict]) -> str | None:
        key = self._cache_key(messages)
        return self._cache.get(key)

    def set(self, messages: list[dict], response: str) -> None:
        key = self._cache_key(messages)
        self._cache[key] = response
        self._save_cache()

    def _load_cache(self) -> None:
        if self._cache_file and os.path.exists(self._cache_file):
            with open(self._cache_file) as f:
                self._cache = json.load(f)

    def _save_cache(self) -> None:
        if self._cache_file:
            with open(self._cache_file, "w") as f:
                json.dump(self._cache, f)
```

**Considerations**:
- Semantic equivalence vs exact match
- Cache size management
- Persistent vs in-memory
- Temperature and randomness

### 3. Token Counting with Caching

**Goal**: Accurate token counting with result caching.

```python
import tiktoken

class TokenCounter:
    def __init__(self, model: str = "gpt-4"):
        self._tokenizer = tiktoken.encoding_for_model(model)
        self._token_cache: dict[str, int] = {}

    def count_tokens(self, text: str) -> int:
        # Check cache
        if text in self._token_cache:
            return self._token_cache[text]

        # Count tokens
        tokens = self._tokenizer.encode(text)
        count = len(tokens)

        # Cache result
        self._token_cache[text] = count
        return count

    def count_messages(self, messages: list[dict]) -> int:
        total = 0
        for msg in messages:
            # Count role + content
            total += self.count_tokens(msg.get("role", ""))
            total += self.count_tokens(msg.get("content", ""))
        return total
```

**Usage**:
```python
counter = TokenCounter(model="gpt-4")

# Count tokens in message history
token_count = counter.count_messages(manager.to_messages())

# Token-aware pruning
if token_count > max_tokens:
    manager.prune(keep_last_n_steps(10))
```

### 4. Memoization Decorator

**Goal**: Generic memoization for pure functions.

```python
from functools import wraps

def memoize(max_size: int = 128):
    def decorator(func):
        cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = (args, tuple(sorted(kwargs.items())))

            if key not in cache:
                if len(cache) >= max_size:
                    # Simple FIFO eviction
                    cache.pop(next(iter(cache)))
                cache[key] = func(*args, **kwargs)

            return cache[key]

        def clear():
            cache.clear()

        wrapper.clear = clear
        return wrapper

    return decorator
```

**Usage**:
```python
@memoize(max_size=100)
def expensive_computation(x: int, y: int) -> int:
    # Expensive operation
    return result

# First call executes
result1 = expensive_computation(5, 10)

# Subsequent calls use cache
result2 = expensive_computation(5, 10)  # Cache hit
```

## Recommendations

### 1. Add Token Counting

**Priority**: High

**Why**:
- Essential for token-aware pruning
- Enables cost optimization
- Provides usage visibility

**Implementation**:
```python
# Use tiktoken for OpenAI models
# Use anthropic for Anthropic models
# Add token counting to MemoryManager
```

### 2. Consider Selective Caching

**Priority**: Medium

**What to cache**:
- File reads (if file unchanged)
- Expensive API calls (if idempotent)
- Repeated computations (if pure)

**What not to cache**:
- Stateful operations
- Time-sensitive data
- Operations with side effects

### 3. Implement Cache Invalidation

**Priority**: High (if caching is added)

**Strategies**:
- **Time-based**: TTL for cache entries
- **Size-based**: LRU eviction
- **Explicit**: Manual invalidation API
- **Event-based**: Invalidate on state changes

### 4. Add Cache Monitoring

**Priority**: Medium

**Metrics to track**:
- Cache hit rate
- Cache size
- Eviction rate
- Memory usage

**Implementation**:
```python
class CacheMonitor:
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def record_hit(self) -> None:
        self.hits += 1

    def record_miss(self) -> None:
        self.misses += 1

    def record_eviction(self) -> None:
        self.evictions += 1

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0
        self.evictions = 0
```

### 5. Document Caching Decisions

**Priority**: High

**What to document**:
- What is cached and why
- Cache invalidation strategy
- Performance impact
- Known limitations

## Current Limitations

1. **No token visibility**: Can't measure actual token usage
2. **No result caching**: Repeated operations execute every time
3. **No memoization**: Expensive computations not optimized
4. **No cache controls**: No way to configure caching behavior
5. **No monitoring**: Can't track cache effectiveness

## Tradeoffs

### Complexity vs Performance

- **No caching**: Simple but potentially slow
- **Simple caching**: Some complexity, moderate speedup
- **Advanced caching**: High complexity, significant speedup

### Memory vs Speed

- **No cache**: Low memory, slower execution
- **Small cache**: Moderate memory, faster execution
- **Large cache**: High memory, fastest execution

### Correctness vs Optimization

- **No caching**: Always correct, no bugs from cache staleness
- **Caching**: Risk of stale data, need invalidation

## Conclusion

tinyAgent currently has **no caching mechanisms**. This is a valid design choice for simplicity and correctness, but there are opportunities for optimization:

1. **Token counting** should be added for cost management
2. **Selective caching** could improve performance for repeated operations
3. **Scratchpad** provides explicit state management (not caching)
4. **Execution limits** prevent output bloat (not caching)

The decision to add caching should be based on:
- Performance requirements
- Use case patterns
- Complexity tolerance
- Maintenance considerations
