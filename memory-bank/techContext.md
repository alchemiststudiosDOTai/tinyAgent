# Technical Context

## Core Technologies

- Python 3.10 (primary development language)
- TypeScript (MCP server/client implementation)
- Markdown (documentation format)
- Mermaid.js (architecture diagrams)

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Setup MCP components
cd mcp && npm install
```

## Key Dependencies

- FastAPI (CLI command routing)
- Pytest (testing framework)
- Typescript 4.9 (MCP implementation)
- Websockets (agent-server communication)

## Tool Usage Patterns

```python
# Typical tool registration
@tool("search_files")
def search_files(path: str, regex: str):
    """Search files with regex pattern"""
    # Implementation...
```

## Technical Constraints

1. Python 3.10+ required
2. MCP servers must implement SSE protocol
3. Memory Bank files must be UTF-8 encoded
4. CLI requires TTY environment
