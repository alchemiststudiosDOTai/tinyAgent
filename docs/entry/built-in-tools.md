---
title: Built-in Tools
path: tinyagent/tools/builtin/
type: directory
depth: 2
description: Pre-built tools for web search, planning, and web browsing
exports:
  - web_search
  - web_browse
  - create_plan
  - get_plan
  - update_plan
seams: [E]
---

# Built-in Tools

Pre-built tools included with the framework for common tasks like web search, web browsing, and planning.

## Available Tools

### Web Tools

#### web_search

Search the web using Brave Search API.

**Function Signature:**
```python
@tool
def web_search(query: str) -> str:
    """Search the web and return formatted results."""
```

**Parameters:**
- `query` (str): Search query string

**Returns:** Formatted string with search results

**Requirements:**
- `BRAVE_API_KEY` environment variable
- `httpx` package

**Usage Example:**
```python
from tinyagent import ReactAgent, web_search

agent = ReactAgent(tools=[web_search])
result = agent.run_sync(
    "Search for recent Python updates"
)
```

**Output Format:**
```
1. Title of result
   Description: Summary of the page
   URL: https://example.com/page

2. Another result
   Description: Another summary
   URL: https://example.com/another
```

**Environment Setup:**
```bash
export BRAVE_API_KEY="your_api_key_here"
```

#### web_browse

Fetch and convert a web page to Markdown.

**Function Signature:**
```python
@tool
def web_browse(url: str) -> str:
    """Fetch URL and return page content as Markdown."""
```

**Parameters:**
- `url` (str): URL to fetch

**Returns:** Page content as Markdown string

**Requirements:**
- `httpx` package
- `markdownify` package

**Usage Example:**
```python
from tinyagent import ReactAgent, web_browse

agent = ReactAgent(tools=[web_browse])
result = agent.run_sync(
    "Browse https://example.com and summarize"
)
```

**Features:**
- Converts HTML to clean Markdown
- Removes scripts, styles, navigation
- Preserves main content
- Handles relative links

### Planning Tools

#### create_plan

Create a new plan with goal and context.

**Function Signature:**
```python
@tool
def create_plan(goal: str, context: str = "") -> str:
    """Create a new plan and return plan ID."""
```

**Parameters:**
- `goal` (str): Plan objective/goal
- `context` (str, optional): Additional context

**Returns:** Plan ID for future reference

**Usage Example:**
```python
from tinyagent import TinyCodeAgent, create_plan

agent = TinyCodeAgent(tools=[create_plan])
result = agent.run_sync("""
Create a plan to analyze the sales data.
Goal: Calculate monthly revenue trends
""")
```

**Plan Structure:**
```python
{
    "plan_id": "uuid",
    "goal": "Plan objective",
    "context": "Additional context",
    "steps": [],
    "status": "created",
    "created_at": "2024-01-01T00:00:00Z"
}
```

#### get_plan

Retrieve a previously created plan.

**Function Signature:**
```python
@tool
def get_plan(plan_id: str) -> str:
    """Get plan details by ID."""
```

**Parameters:**
- `plan_id` (str): Plan identifier from `create_plan`

**Returns:** Plan details as JSON string

**Usage Example:**
```python
from tinyagent import TinyCodeAgent, get_plan

agent = TinyCodeAgent(tools=[get_plan])
result = agent.run_sync("""
Get the plan with ID 'abc-123' and show its details
""")
```

#### update_plan

Update an existing plan's goal, steps, or status.

**Function Signature:**
```python
@tool
def update_plan(
    plan_id: str,
    goal: str | None = None,
    steps: list[str] | None = None,
    status: str | None = None
) -> str:
    """Update plan and return updated plan."""
```

**Parameters:**
- `plan_id` (str): Plan identifier
- `goal` (str, optional): New goal
- `steps` (list[str], optional): New steps
- `status` (str, optional): New status

**Returns:** Updated plan as JSON string

**Usage Example:**
```python
from tinyagent import TinyCodeAgent, update_plan

agent = TinyCodeAgent(tools=[update_plan])
result = agent.run_sync("""
Update plan 'abc-123' with these steps:
1. Load data from CSV
2. Calculate monthly totals
3. Generate trend chart
""")
```

**Status Values:**
- `"created"` - Plan initialized
- `"in_progress"` - Plan being executed
- `"completed"` - Plan finished
- `"blocked"` - Plan blocked
- `"cancelled"` - Plan cancelled

## Tool Registration

### Importing Individual Tools

```python
from tinyagent import web_search, web_browse

agent = ReactAgent(tools=[web_search, web_browse])
```

### Importing All Built-in Tools

```python
from tinyagent.tools import (
    web_search,
    web_browse,
    create_plan,
    get_plan,
    update_plan
)

agent = ReactAgent(tools=[
    web_search,
    web_browse,
    create_plan,
    get_plan,
    update_plan
])
```

## Implementation Details

### web_search Implementation

```python
import httpx
import os

async def web_search(query: str) -> str:
    """Search using Brave Search API."""
    api_key = os.getenv("BRAVE_API_KEY")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query},
            headers={"Accept": "application/json"},
            auth=(api_key, "")
        )
        results = response.json()["web"]["results"]
        return format_results(results)
```

### web_browse Implementation

```python
import httpx
from markdownify import markdownify

async def web_browse(url: str) -> str:
    """Fetch URL and convert to Markdown."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        html = response.text
        markdown = markdownify(html)
        return markdown
```

### Planning Tools Implementation

Plans are stored in-memory (can be extended for persistence):

```python
_plans: dict[str, dict] = {}

def create_plan(goal: str, context: str = "") -> str:
    """Create and store a new plan."""
    plan_id = str(uuid.uuid4())
    plan = {
        "plan_id": plan_id,
        "goal": goal,
        "context": context,
        "steps": [],
        "status": "created",
        "created_at": datetime.utcnow().isoformat()
    }
    _plans[plan_id] = plan
    return plan_id

def get_plan(plan_id: str) -> str:
    """Retrieve plan by ID."""
    plan = _plans.get(plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")
    return json.dumps(plan)

def update_plan(
    plan_id: str,
    goal: str | None = None,
    steps: list[str] | None = None,
    status: str | None = None
) -> str:
    """Update plan fields."""
    plan = _plans.get(plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    if goal is not None:
        plan["goal"] = goal
    if steps is not None:
        plan["steps"] = steps
    if status is not None:
        plan["status"] = status

    return json.dumps(plan)
```

## Error Handling

### Missing API Key

```python
from tinyagent import web_search

# BRAVE_API_KEY not set
try:
    await web_search.run({"query": "test"})
except ValueError as e:
    print(f"Error: {e}")
    # "BRAVE_API_KEY environment variable not set"
```

### Invalid URL

```python
from tinyagent import web_browse

# Invalid URL
try:
    await web_browse.run({"url": "not-a-url"})
except httpx.InvalidURL as e:
    print(f"Invalid URL: {e}")
```

### Plan Not Found

```python
from tinyagent import get_plan

# Plan doesn't exist
try:
    await get_plan.run({"plan_id": "nonexistent"})
except ValueError as e:
    print(f"Error: {e}")
    # "Plan nonexistent not found"
```

## Best Practices

1. **Set API keys** before using web tools
2. **Handle errors** gracefully in agent prompts
3. **Use plan tools** for multi-step tasks
4. **Combine tools** for complex workflows
5. **Validate URLs** before browsing
6. **Rate limit** web requests
7. **Cache results** when appropriate
8. **Monitor API usage** and costs

## Example Workflows

### Research Task

```python
from tinyagent import ReactAgent, web_search, web_browse

agent = ReactAgent(tools=[web_search, web_browse])
agent.run_sync("""
1. Search for "Python async await best practices"
2. Browse the top 3 results
3. Summarize the key recommendations
""")
```

### Multi-Step Planning

```python
from tinyagent import TinyCodeAgent, create_plan, get_plan, update_plan

agent = TinyCodeAgent(tools=[
    create_plan,
    get_plan,
    update_plan
])
agent.run_sync("""
Create a plan to analyze a dataset:
1. Create plan with goal and context
2. Update plan with specific steps
3. Get plan to verify it's correct
4. Execute the plan steps
""")
```

### Combined Tools

```python
from tinyagent import ReactAgent, web_search, web_browse, create_plan

agent = ReactAgent(tools=[
    web_search,
    web_browse,
    create_plan
])
agent.run_sync("""
Research a topic and create a plan:
1. Search for information
2. Browse relevant pages
3. Create a plan based on findings
4. Update plan with specific actions
""")
```

## Extending Built-in Tools

### Custom Search Tool

```python
from tinyagent import tool
import httpx

@tool
def custom_search(query: str, max_results: int = 5) -> str:
    """Custom search with result limit."""
    # Implementation
    return formatted_results

agent = ReactAgent(tools=[custom_search])
```

### Custom Browse Tool

```python
from tinyagent import tool
import httpx
from bs4 import BeautifulSoup

@tool
def browse_and_extract(
    url: str,
    selector: str
) -> str:
    """Browse and extract specific elements."""
    response = httpx.get(url).text
    soup = BeautifulSoup(response, 'html.parser')
    elements = soup.select(selector)
    return "\n".join(e.get_text() for e in elements)

agent = ReactAgent(tools=[browse_and_extract])
```

## Dependencies

Required packages for built-in tools:

```bash
# From pyproject.toml or requirements.txt
httpx>=0.24.0
markdownify>=0.11.6
beautifulsoup4>=4.12.0  # Optional for advanced parsing
```

Install with:
```bash
uv pip install httpx markdownify beautifulsoup4
```

## Configuration

### Environment Variables

```bash
# Required for web_search
export BRAVE_API_KEY="your_brave_api_key"

# Optional: Custom timeout
export WEB_SEARCH_TIMEOUT="30"

# Optional: Custom user agent
export WEB_BROWSE_USER_AGENT="MyAgent/1.0"
```

### Tool Configuration

```python
import os

# Configure web search timeout
os.environ["WEB_SEARCH_TIMEOUT"] = "60"

# Configure browse user agent
os.environ["WEB_BROWSE_USER_AGENT"] = "MyAgent/1.0"
```

## Future Enhancements

Planned additions to built-in tools:
- File system operations (read, write, list)
- Database queries (SQL, NoSQL)
- API clients (GitHub, Twitter, etc.)
- Data processing (CSV, JSON, Excel)
- Date/time utilities
- Math and statistics functions
- Image processing
- Email operations

## Tool Standards

All built-in tools must adhere to strict uniformity standards to ensure consistent behavior within the agent framework. These standards are enforced by automated tests (`tests/test_tools_uniformity.py`).

### Requirements

1.  **Name**: Every tool must have a non-empty `name` attribute.
2.  **Documentation**: Every tool must have a meaningful, non-empty docstring (`doc` attribute).
3.  **Schema**: Every tool must provide a valid JSON schema via `json_schema`, where the root type is `"object"`.

### Verification

To verify that all built-in tools meet these standards, run:

```bash
pytest tests/test_tools_uniformity.py
```
