---
title: Built-in Tools
path: tools/builtin/
type: directory
depth: 1
description: Standard tool implementations for planning, web browsing, and web search
exports: [create_plan, update_plan, get_plan, web_browse, web_search]
seams: [M]
---

# tools/builtin/

## Where
`/Users/tuna/tinyAgent/tinyagent/tools/builtin/`

## What
Provides standard tool implementations for common agent capabilities: task planning, web content retrieval, and web search. All tools registered via `@tool` decorator for agent use.

## How

### planning.py

**Purpose**: In-memory plan management for agents

**Tools:**
- `create_plan(goal: str, context: str = "") -> dict`: Creates new plan with unique ID
- `update_plan(plan_id: str, updates: dict) -> dict`: Modifies existing plan
- `get_plan(plan_id: str) -> dict`: Retrieves plan by ID

**Storage:**
- `_PLANS`: In-memory dictionary keyed by plan ID
- `_validate_steps`: Ensures steps are list of strings
- UUID-based unique identifiers

**Use Case**: Agents manage multi-step task breakdown and progress tracking

### web_browse.py

**Purpose**: Fetch and convert web content to Markdown

**Tool:**
- `web_browse(url: str, headers: dict | None = None) -> str`
  - Makes GET request using `httpx`
  - Converts HTML to Markdown via `markdownify`
  - Handles network errors and missing content

**Design:**
- Async for non-blocking requests
- Defensive import of `markdownify`
- Strips presentation complexity

**Use Case**: Agents read documentation, articles, web pages

### web_search.py

**Purpose**: Web search via Brave Search API

**Tool:**
- `web_search(query: str) -> str`
  - Queries Brave Search API
  - Returns formatted top results (title, description, URL)
  - Requires `BRAVE_SEARCH_API_KEY` environment variable

**Error Handling:**
- API key absence
- Network issues
- Unsuccessful API responses

**Use Case**: Agents gather current information, find relevant links

## Why

**Design Rationale:**
- **Planning Tools**: Simple, ephemeral state management without persistence
- **Web Browse**: "Eyes" on internet, Markdown for LLM-friendly format
- **Web Search**: External knowledge access via specialized API
- **Modularity**: Each tool focused on single capability
- **@tool Decorator**: Automatic registration and validation

**Architectural Role:**
- **Agent Capabilities**: Extend what agents can do
- **Knowledge Access**: Web search and browse for external information
- **Task Management**: Planning tools for complex multi-step operations
- **Integration**: Registered via `core.registry.tool` decorator

**Dependencies:**
- `core.registry.tool`: Registration decorator
- `httpx`: Async HTTP client
- `markdownify`: HTML to Markdown conversion
- `uuid`: Unique identifiers
- `os`: Environment variables
