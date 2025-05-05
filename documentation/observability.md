# Observability in tinyAgent

This document details the implementation of observability features, primarily distributed tracing using OpenTelemetry, within the tinyAgent framework.

## Purpose

Observability provides insights into the agent's behavior, performance, and potential issues. Distributed tracing allows us to follow requests as they flow through different components (LLM calls, tool executions, internal logic), making it easier to:

- Diagnose latency issues.
- Understand complex execution flows.
- Identify errors and their root causes.
- Monitor system performance over time.

## Implementation Details

The core observability features are built around the OpenTelemetry standard.

### 1. OpenTelemetry Integration (`src/tinyagent/observability/tracer.py`)

- **Configuration (`configure_tracing`)**:
  - This function initializes the global OpenTelemetry `TracerProvider`.
  - It reads settings from the `observability.tracing` section in `config.yml`.
  - It's designed to be idempotent (safe to call multiple times) and thread-safe.
  - It supports different exporters (`console`, `otlp`, `sqlite`) based on the configuration.
  - If tracing is disabled (`enabled: false`), it sets up a `NoOpTracerProvider` to minimize performance impact and prevents exporter initialization.
- **Tracer Retrieval (`get_tracer`)**:
  - Provides a cached way to get a `Tracer` instance based on the current global configuration.
  - Returns a `NoOpTracer` if tracing has not been explicitly enabled via `configure_tracing`.
- **Agent Tracing Decorator (`@trace_agent_run`)**:
  - This decorator is specifically designed to wrap the `run` method of Agent instances.
  - It automatically creates a top-level span named `agent.run` for the execution.
  - Records the agent's prompt, model used, and final response as span attributes.
  - Handles errors and sets the span status appropriately.

### 2. Agent Implementation (`src/tinyagent/agent.py`)

- **Base `Agent`**: Does **not** have its `run` method traced by default. Its `execute_tool_call` method also does **not** create spans.
- **`TracedAgent` Subclass**:
  - Inherits from `Agent`.
  - Its `run` method is decorated with `@trace_agent_run`, enabling tracing for the overall agent execution.
  - It **overrides** the `execute_tool_call` method to specifically add trace spans for tool executions initiated by this agent subclass.

### 3. Agent Factory (`src/tinyagent/factory/agent_factory.py`)

- The `tiny_agent()` helper function uses the `AgentFactory`.
- The factory decides whether to return a base `Agent` or a `TracedAgent` based on the `trace_this_agent` argument passed to `tiny_agent()`:
  - `tiny_agent(..., trace_this_agent=True)`: Returns a `TracedAgent` (Tracing ON).
  - `tiny_agent(..., trace_this_agent=False)`: Returns a base `Agent` (Tracing OFF).
  - `tiny_agent(...)` (default, flag omitted): Returns a base `Agent` (Tracing OFF, respecting the principle that default should be off). _Note: Previously, this default checked global config, but has been simplified._

### 4. Configuration (`config.yml`)

Tracing behavior is controlled via the `observability.tracing` section:

```yaml
observability:
  tracing:
    enabled: true # Master switch for tracing (true/false) - affects configure_tracing default
    service_name: "tinyagent" # Name identifying this service in traces
    sampling_rate: 1.0 # Fraction of traces to sample (0.0 to 1.0)
    exporter:
      # Exporter type: "console", "otlp", or "sqlite"
      type: "sqlite" # How to export traces ("console", "otlp", or "sqlite" for database)
      # OTLP specific settings (only used if type is "otlp")
      endpoint: "http://localhost:4317" # OTLP collector endpoint URL
      headers: {} # Optional headers for OTLP exporter (e.g., auth)
      # SQLite specific settings (only used if type is "sqlite")
      db_path: "traces.db" # Path where the SQLite database file will be created/used
    attributes: # Extra key-value attributes added to all spans
      environment: "development"
      version: "0.1.0" # Placeholder version
```

### 5. SQLite Exporter & Traceboard Viewer

- **Exporter (`src/tinyagent/observability/sqlite_exporter.py`)**:
  - When configured (`type: "sqlite"`), this exporter writes trace span data directly to a specified SQLite database file (`db_path`).
  - Automatically creates the necessary database schema if the file doesn't exist or is empty.
- **Traceboard (`src/tinyagent/observability/traceboard.py`)**:
  - A simple FastAPI web application to view traces stored in the SQLite database.
  - Requires `fastapi` and `uvicorn` (installed as dependencies of `tinyagent`).
  - **Launching the Traceboard:**
    - If you have installed `tinyagent` (e.g., `pip install .` in the project root), the necessary libraries are available.
    - You can launch the server by directly executing the `traceboard.py` script using Python.
    - Navigate to your project's root directory in the terminal.
    - Run the following command, pointing it to your trace database:
      ```bash
      python src/tinyagent/observability/traceboard.py --db traces.db
      ```
    - Optional arguments:
      - `--host <ip_address>` (default: `127.0.0.1`)
      - `--port <port_number>` (default: `8000`)
    - Access the traceboard in your web browser at the specified host and port (e.g., `http://127.0.0.1:8000`).

## What Observability Looks Like

When tracing is enabled, you get detailed visibility into your agent's operations. Here's what to expect:

### 1. Trace List View

The Traceboard main page displays a list of all traces in the database:

```
TinyAgent Traceboard

Trace List:
- d5702744c348f34b6d3cd33b1dfb7898 (test.manual_execution) - 2024-07-05 12:30:02
  Duration: 152.3ms | Service: test_traceboard_smoke

[... other traces would be listed here ...]
```

Each trace shows:

- A unique trace ID
- The name of the root span (typically "agent.run" for agent calls)
- When the trace was created
- The total duration
- The service name from your configuration

### 2. Trace Detail View

Clicking on a trace ID takes you to a detailed view showing the hierarchical span structure:

```
Trace Detail - d5702744c348f34b6d3cd33b1dfb7898

Root Span: test.manual_execution
Duration: 152.3ms
Service: test_traceboard_smoke
Start Time: 2024-07-05 12:30:02.345

Attributes:
- test.function: simple_math_test
- test.a: 55
- test.b: 45
- test.result: 100
- test.run_id: 1746482602.432

Child Spans:
└── simple_math_test
    Duration: 98.1ms
    Attributes:
    - tool.name: simple_math_test
    - argument.a: 55
    - argument.b: 45
    - return.value: 100
```

### 3. Agent Execution Trace Example

In a more typical agent execution, you'd see a more complex trace structure:

```
Trace Detail - c6e92a17b45d8f29a13edf45c9ab6721

Root Span: agent.run
Duration: 3.25s
Service: tinyagent
Start Time: 2024-07-05 12:15:23.789

Attributes:
- agent.prompt: "Calculate the sum of 123 and 456"
- agent.model: "deepseek/deepseek-chat"
- agent.response: "The sum of 123 and 456 is 579."

Child Spans:
├── llm.completion_request
│   Duration: 2.43s
│   Attributes:
│   - llm.model: "deepseek/deepseek-chat"
│   - llm.prompt_tokens: 128
│   - llm.completion_tokens: 45
│   - llm.total_tokens: 173
│
└── tool.execute
    Duration: 0.58s
    Attributes:
    - tool.name: "calculate_sum"
    - argument.a: 123
    - argument.b: 456
    - return.value: 579
```

### 4. Error Case Example

When an error occurs, spans capture the exception information:

```
Trace Detail - a8f67c21d9e45b32f89c10ad5e823f56

Root Span: agent.run (Status: ERROR)
Duration: 1.87s
Service: tinyagent
Start Time: 2024-07-05 12:22:45.123

Attributes:
- agent.prompt: "Calculate the sum of 'hello' and 456"
- agent.model: "deepseek/deepseek-chat"
- error.type: "TypeError"
- error.message: "Cannot convert string to integer: 'hello'"

Child Spans:
├── llm.completion_request
│   Duration: 1.43s
│   Attributes:
│   - llm.model: "deepseek/deepseek-chat"
│   - llm.prompt_tokens: 132
│   - llm.completion_tokens: 38
│   - llm.total_tokens: 170
│
└── tool.execute (Status: ERROR)
    Duration: 0.31s
    Attributes:
    - tool.name: "calculate_sum"
    - argument.a: "hello"
    - argument.b: 456
    - error.type: "TypeError"
    - error.message: "Cannot convert string to integer: 'hello'"
```

### 5. Benefits of this Visualization

The traceboard visualization provides:

1. **Timeline**: Precise timing information showing where time is spent
2. **Hierarchy**: Clear parent-child relationships between spans
3. **Contextual Data**: Important attributes like inputs and outputs
4. **Error Tracking**: Detailed error information when things go wrong
5. **Filtering**: (In more advanced implementations) Ability to filter by time, service, or error status

These visualizations help you:

- Identify performance bottlenecks (e.g., slow tool execution or LLM calls)
- Debug errors by seeing the exact context and chain of events
- Understand how your agent processes complex requests
- Verify that tools receive the expected arguments and return the expected values

## Usage

To enable tracing for a specific agent instance, use the `trace_this_agent=True` flag when creating it with `tiny_agent`:

```python
from tinyagent.agent import tiny_agent
from tinyagent.observability.tracer import configure_tracing # Needed to enable tracing

# 1. Ensure tracing is configured and enabled globally (e.g., using config.yml)
#    This call reads config.yml or uses defaults if tracing not already setup.
#    If config.yml has enabled: true and type: sqlite, this sets up the SQLite exporter.
configure_tracing()

# 2. Create the agent, explicitly requesting tracing for this instance
agent = tiny_agent(tools=[my_tool_function], trace_this_agent=True)

# 3. Run the agent - its execution and tool calls will be traced
result = agent.run("Use my tool...")
```

To create an agent _without_ tracing, simply omit the flag or set it to `False`:

```python
# Create an agent - tracing will be OFF by default for this instance
agent_no_trace = tiny_agent(tools=[my_tool_function])
# or explicitly
agent_no_trace_explicit = tiny_agent(tools=[my_tool_function], trace_this_agent=False)

# Running this agent will not produce traces
result_no_trace = agent_no_trace.run("Use my tool again...")
```

## Testing

- **Default Behavior**: Use `tiny_agent(...)` without the flag to test the default non-traced behavior.
- **Enabled Behavior**: Use `tiny_agent(..., trace_this_agent=True)` to test traced execution. Ensure `configure_tracing()` has been called appropriately for the test environment (using either the default config or a test-specific one).
- **SQLite/Traceboard**: See `tests/07_test_sqlite_traceboard_smoke.py` for an example of testing the SQLite exporter and traceboard functionality. This test explicitly configures tracing using the SQLite exporter for its scope.

## Future Considerations

- **Log Correlation**: Automatically inject `trace_id` and `span_id` into log records.
- **Metrics**: Add OpenTelemetry metrics for monitoring request counts, durations, error rates, etc.
- **Context Propagation**: Ensure trace context is correctly propagated across asynchronous boundaries or network calls if more complex interactions are added.
- **Enhanced Visualization**: Develop a more interactive traceboard with search, filtering, and graphical timeline views.
- **Retention Policies**: Implement automatic cleanup of old trace data to prevent database growth.
- **Performance Analysis**: Add statistical analysis of common operations and trend monitoring over time.
