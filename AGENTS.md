Core Workflow

Reason before acting. Follow the ReAct pattern — always explain why before doing.
Example:
Reason: I need to verify if this feature has baseline tests.
Act: Search tests/ for existing coverage.
No vague objectives. Never write code until the problem is explicitly defined.
Small diffs, frequent commits. Ship incremental progress, not monoliths.
Ask or infer. If the goal is unclear, clarify or apply best practices — but never assume silently.
Sync .claude after every material change. Keeping the knowledge base current is part of your job. Use the claude-kb CLI to maintain KB entries: add new patterns/components, update existing documentation, validate schema integrity, and sync the manifest to track changes across commits.
Refer to `documentation/architecture/` (especially `documentation/architecture/agents/`) before changing agent code or tooling; keep docs in sync with design intent.

**KB Workflow**
- Capture every meaningful fix, feature, or debugging pattern immediately with `claude-kb add` (pick the right entry type, set `--component`, keep the summary actionable, and include error + solution context).
- If you are iterating on an existing pattern, prefer `claude-kb update` so history stays linear; the command fails loudly if the entry is missing—stop and audit instead of recreating it.
- Once the entry is accurate, run `claude-kb sync --verbose` to refresh `.claude/manifest.json` and surface drift against the repo.
- Finish with `claude-kb validate` to guarantee schema integrity before you move on; do not skip even for small edits.
- When cleaning up stale knowledge, use `claude-kb delete …` and immediately re-run `sync` + `validate` so Git reflects the removal.
- Treat the KB like production code: review diffs, keep entries typed, and never leave `.claude/` out of sync with the changes you just shipped.

.claude layout
The tool keeps everything under .claude/ and will create the folders on demand:

.claude/
  metadata/      component summaries
  debug_history/ debugging timelines
  qa/            question & answer entries
  code_index/    file references
  patterns/      reusable fixes or snippets
  cheatsheets/   quick reference sections
  manifest.json  last sync snapshot
Everyday workflow
# create a typed entry
claude-kb add pattern --component ui.auth --summary "Retry login" \
  --error "Explain retry UX" --solution "Link to pattern doc"

# modify an existing entry (errors when the item is missing)
claude-kb update pattern --component ui.auth \
  --error "Retry login" --solution "Updated copy"

# list or validate your KB
claude-kb list --type pattern
claude-kb validate

# sync manifest and inspect git drift
claude-kb sync --verbose
claude-kb diff --since HEAD~3

# remove stale data
claude-kb delete pattern --component ui.auth

- **STOP** - Read existing code before writing anything
- **SEARCH** codebase for patterns and dependencies
- **NEVER** assume libraries exist - check imports first
- **PRE-COMMIT HOOKS** these must be ran, they can be skipped, if the issue is minor





## Project Map
```
tinyagent/
├── agents/
│   ├── agent.py      # ReactAgent - orchestrates ReAct loop
│   └── code_agent.py # TinyCodeAgent - Python code executor
├── tools.py      # @tool decorator & global registry
├── prompt.py     # System/error prompt templates
├── tests/        # Test suite
└── examples/
    ├── simple_demo.py    # Minimal setup and basic usage
    ├── react_demo.py     # Enhanced features (scratchpad, error recovery, observations)
    ├── code_demo.py      # Python code execution capabilities
    └── web_search_tool.py # Web search integration example
documentation/
├── modules/
│   ├── tools.md            # Comprehensive tools guide
│   └── tools_one_pager.md  # One-page tools quickstart
```

Default structure

Folder = the concept / feature

Files = roles inside that concept

Aim for 2–5 files per concept. Don’t chase tiny files. Don’t allow god-files.

The 4 triggers to split a file

Split when any of these happen:

The file has two jobs (you can say “it does X and Y”)

You edit it for unrelated reasons

You can’t describe it in one sentence without “and”

Everyone imports it everywhere / it becomes a dependency magnet

The 3 buckets (keep them from mixing)

Policy = rules/decisions (“what should happen”)

Mechanism = DB/HTTP/framework (“how it happens”)

Presentation = response shapes/UI (“how it’s shown”)

Mixing all 3 in one file = usually tangled.

Folder boundary test (best test)

If we change the rules for a concept, only this folder should change.


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

#### Testing Philosophy
**Contrastive Negative Testing**: Prove the rule works by showing the good passes and the bad fails.
- Create nearly identical test cases (good vs bad)
- Good example validates the rule
- Bad example has small, realistic violations
- Easy side-by-side comparison
- Clear cause-and-effect for each violation

#### Setup Options

```bash
uv venv                    # Creates .venv/
source .venv/bin/activate  # Activate environment

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
# CORRECT - Import from main package (public API)
from tinyagent.tools import tool
from tinyagent import ReactAgent

# CORRECT - Import from agents subpackage (internal structure)
from tinyagent.agents.agent import ReactAgent

# WRONG
from .tool import tool
from .react import ReactAgent
```

### 6. Common Commands
```bash
# Setup
source .venv/bin/activate && pre-commit install

# Development
python examples/simple_demo.py     # Basic usage demo
python examples/react_demo.py     # Enhanced features demo
python examples/code_demo.py      # Code execution demo
python examples/web_search_tool.py # Web search demo
ruff check . --fix               # Fix linting
ruff format .                    # Format code

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

- Confirm context and dependencies before touching code.

| Step    | Principle                                   | Tooling Focus            |
| ------- | ------------------------------------------- | ------------------------ |
| Define  | Explicit problem definition before any code | Issue / PR description   |
| Test    | Golden baseline plus failing test first     | `pytest`, `hatch run test` |
| Build   | Small, typed, composable change             | `ruff`, `mypy`           |
| Document | Keep `.claude` and docs in sync             | `claude-kb add/sync/validate`, docs update |
| Review  | Peer review or self-inspection              | PR checklist             |

- Run `ruff check --fix .` and `ruff format .` before committing.
- Re-run the targeted pytest suite before and after changes.
- Verify pre-commit hooks pass (use `git commit -n` only if instructed).

## CRITICAL REMINDERS

**TEST FIRST** - No exceptions
**RUFF ALWAYS** - Before committing
**MATCH PATTERNS** - Follow existing code style exactly
**ASK IF UNSURE** - User prefers questions over mistakes

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
