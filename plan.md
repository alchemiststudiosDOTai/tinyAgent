# Web Browse Tool Implementation Plan

## Overview
Build a web scraping/viewing tool using `requests` and `markdownify` for local web content fetching and conversion to markdown.

## Design Decisions
- **Content Type Handling**: Return error message for non-HTML content (PDFs, images, JSON, etc.)
- **HTML Cleanup**: Strip `<script>`, `<style>`, and HTML comments before markdown conversion
- **Features**: Support custom HTTP headers (user-agent, auth, etc.)

## Changes Required

### 1. Add markdownify dependency
**File**: `pyproject.toml`
- Add `markdownify>=0.11.0` to dependencies list (around line 29, after requests)
- Note: `requests>=2.31.0` already exists

### 2. Create new builtin tool
**File**: `tinyagent/tools/builtin/web_browse.py`

**Function Signature**:
```python
@tool
def web_browse(url: str, headers: dict[str, str] | None = None) -> str:
    """Fetch a web page and convert it to markdown.

    Args:
        url: The URL to fetch
        headers: Optional HTTP headers (user-agent, authorization, etc.)

    Returns:
        Markdown-formatted content or error message
    """
```

**Implementation Details**:
- Import pattern: `import requests  # type: ignore[import-untyped]`
- Import markdownify: `from markdownify import markdownify`
- URL validation (basic format check)
- HTTP GET request with 10s timeout (matching web_search pattern)
- Content-type validation:
  - Check response headers for `text/html`
  - Return error string if not HTML
- HTML cleanup:
  - Use BeautifulSoup or regex to strip `<script>`, `<style>`, HTML comments
  - Keep the HTML structure intact for markdown conversion
- Convert cleaned HTML to markdown using `markdownify()`
- Custom headers support:
  - Default headers: `{"User-Agent": "tinyAgent-web-browse/1.0"}`
  - Merge with user-provided headers if supplied
- Error handling (CRITICAL):
  - NEVER raise exceptions - always return error strings
  - Pattern: `try: ... except requests.RequestException as e: return f"Error: {str(e)}"`
  - Handle missing URL: `return "Error: URL is required"`
  - Handle invalid content-type: `return "Error: URL must return HTML content (got: {content_type})"`

**Reference Implementation**: Follow `tinyagent/tools/builtin/web_search.py` pattern

### 3. Update exports
**File**: `tinyagent/tools/builtin/__init__.py`
- Add import: `from .web_browse import web_browse`
- Add to `__all__`: `"web_browse"`

**File**: `tinyagent/tools/__init__.py`
- No changes needed (auto-imports from builtin via existing pattern)

### 4. Create comprehensive tests
**File**: `tests/api_test/test_web_browse.py`

**Test Cases**:
```python
def test_web_browse_valid_url_returns_markdown() -> None:
    """Test successful HTML fetch and markdown conversion."""

def test_web_browse_invalid_url_returns_error() -> None:
    """Test malformed URL handling."""

def test_web_browse_non_html_content_returns_error() -> None:
    """Test that non-HTML content types return error."""

def test_web_browse_custom_headers_applied() -> None:
    """Test custom headers are sent in request."""

def test_web_browse_timeout_handling() -> None:
    """Test timeout error returns error string."""

def test_web_browse_strips_script_and_style() -> None:
    """Test that scripts and styles are removed."""

def test_web_browse_with_react_agent() -> None:
    """Test ReactAgent integration with web_browse tool."""
```

**Reference**: Follow `tests/test_planning_tool.py` pattern for builtin tools

### 5. Optional: Create example/demo
**File**: `examples/web_browse_demo.py` (optional)
- Show direct tool usage
- Show ReactAgent integration
- Example with custom headers

## Testing Protocol

### Before Changes
```bash
source .venv/bin/activate
pytest tests/api_test/test_agent.py -v
```

### During Development
```bash
ruff check . --fix
ruff format .
```

### After Changes
```bash
pytest tests/api_test/test_agent.py -v
pytest tests/api_test/test_web_browse.py -v
pre-commit run --all-files
```

## Implementation Order

1. Add `markdownify` to `pyproject.toml`
2. Create `tinyagent/tools/builtin/web_browse.py` with full implementation
3. Update `tinyagent/tools/builtin/__init__.py` exports
4. Create `tests/api_test/test_web_browse.py` with all test cases
5. Run linting: `ruff check . --fix && ruff format .`
6. Run tests: `pytest tests/api_test/test_agent.py -v`
7. Run new tests: `pytest tests/api_test/test_web_browse.py -v`
8. Fix any pre-commit hook failures
9. (Optional) Create example demo file

## Success Criteria

- All existing tests pass (`test_agent.py`)
- All new tests pass (`test_web_browse.py`)
- Tool successfully converts HTML to markdown
- Non-HTML content returns appropriate errors
- Custom headers work correctly
- Scripts and styles are stripped from output
- Code passes ruff linting and formatting
- Pre-commit hooks pass

## Notes

- Follow CLAUDE.md workflow: test first, small diffs, frequent commits
- Match existing patterns exactly (especially error handling)
- Keep docstrings concise and actionable (they become agent prompts)
- Use type hints always
- Return error strings, never raise exceptions in tool functions
