# CLAUDE.md

## Project Map
```
tinyagent/
├── agent.py      # ReactAgent - orchestrates ReAct loop
├── tools.py      # @tool decorator & global registry
├── prompt.py     # System/error prompt templates
├── tests/        # Test suite
└── examples/     # Demo scripts
```

## Critical Instructions

### 1. ALWAYS Start With Context
- **STOP** - Read existing code before writing anything
- **SEARCH** codebase for patterns and dependencies
- **NEVER** assume libraries exist - check imports first
- **PRE-COMMIT HOOKS** these must NEVER be skipped, you will be punished for skipping the hooks

### 2. Development Workflow
```bash
# BEFORE any changes
source .venv/bin/activate && pytest tests/api_test/test_agent.py -v

# DURING development
ruff check . --fix && ruff format .

# AFTER changes
pytest tests/api_test/test_agent.py -v
pre-commit run --all-files
```

### 3. Setup & Testing Protocol
**MANDATORY**: Tests MUST pass before committing

#### Setup Options

**Option A: UV (Recommended - 10x Faster)**
```bash
uv venv                    # Creates .venv/
source .venv/bin/activate  # Activate environment
uv pip install -e .       # Install project
uv pip install pytest pre-commit  # Install dev deps
```

**Option B: Traditional venv**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -e . && pip install pytest pre-commit
```

#### Testing Commands
```bash
# Run all tests
pytest tests/api_test/test_agent.py -v

# Run specific test
pytest tests/api_test/test_agent.py::TestReactAgent::test_agent_initialization_with_function_tools -v
```

### 4. Code Standards

#### Python Rules
- **USE** type hints ALWAYS
- **MATCH** existing patterns exactly
- **NO** print statements in production code
- **RUN** `ruff check . --fix` after EVERY change

#### Tool Registration
- Functions with `@tool` decorator auto-register in global registry
- ReactAgent accepts raw functions OR Tool objects
- Invalid tools raise ValueError during `__post_init__`

### 5. Critical Implementation Details

#### API Configuration
- Uses OpenAI v1 API: `from openai import OpenAI`
- OpenRouter support via `OPENAI_BASE_URL` env var
- API key: constructor arg > `OPENAI_API_KEY` env var

#### Message Format
**CRITICAL**: Use "user" role for tool responses (OpenRouter compatibility):
```python
{"role": "user", "content": f"Tool '{name}' returned: {result}"}
```

#### Import Pattern
```python
# CORRECT
from tinyagent.tools import tool
from tinyagent.agent import ReactAgent

# WRONG
from .tool import tool
from .react import ReactAgent
```

### 6. Common Commands
```bash
# Setup
source .venv/bin/activate && pre-commit install

# Development
python examples/react_demo.py   # Test examples
ruff check . --fix             # Fix linting
ruff format .                  # Format code

# Testing
pytest tests/api_test/test_agent.py -v # All tests
pre-commit run --all-files             # Full check
```

### 7. Project Configuration
- **Ruff**: Line length 100, Python 3.10+
- **Pre-commit**: Runs ruff + pytest on test_agent.py
- **Environment**: Uses `.env` for API keys

### 8. Error Handling
- **NEVER** swallow errors silently
- **ALWAYS** check tool registration before agent creation
- **STOP** and ask if registry/import issues occur

## Workflow Checklist

1. □ Read existing code patterns
2. □ Check imports and dependencies
3. □ Run tests before changes
4. □ Implement following existing patterns
5. □ Run ruff check/format
6. □ Run tests after changes
7. □ Verify pre-commit hooks pass

## CRITICAL REMINDERS

**TEST FIRST** - No exceptions
**RUFF ALWAYS** - Before committing
**MATCH PATTERNS** - Follow existing code style exactly
**ASK IF UNSURE** - User prefers questions over mistakes
