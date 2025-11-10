# Research – Web Browse Tool Specification

**Date:** 2025-11-09
**Owner:** Claude (research agent)
**Phase:** Research - Tool Specification
**Git Commit:** 5da284341a14031d48f78f91ce56c9b50ec1ca50
**Components:** tools, builtin tools, markdownify, requests
**Tags:** tools, web-browsing, specification, markdown-conversion

## Goal

Define a clear specification for a web browsing tool that allows the AI agent to view website content. The tool should:
- Fetch websites directly (no external API middlemen)
- Convert HTML to Markdown for LLM-friendly consumption
- Be completely local and free (no API keys, no costs)
- Follow existing tinyAgent tool patterns

## Tool Overview

### What It Does

**Purpose**: Allow ReactAgent to browse and read web pages by fetching HTML and converting it to clean Markdown.

**Name**: `web_browse`

**Type**: Builtin tool (located in `tinyagent/tools/builtin/`)

**Input**: URL string (must start with http:// or https://)

**Output**: Markdown-formatted text content from the webpage, or error message string

### Why Markdown?

**Advantages over plain text extraction**:
- ✅ Preserves document structure (headings, lists, links)
- ✅ LLMs are trained on markdown (natural format)
- ✅ Maintains semantic meaning (bold, italic, code blocks)
- ✅ Easier to parse and reason about for agents
- ✅ Cleaner than raw HTML, richer than plain text

**Example transformation**:
```html
<h1>Welcome</h1>
<p>This is <strong>important</strong> content.</p>
<ul>
  <li>Item 1</li>
  <li>Item 2</li>
</ul>
```

Becomes:
```markdown
# Welcome

This is **important** content.

- Item 1
- Item 2
```

## Implementation Approach

### Libraries

**Primary**: `markdownify` + `requests`

**Current Status**:
- `requests>=2.31.0` - ✅ Already in pyproject.toml dependencies
- `markdownify` - ⚠️  Installed in environment but NOT in pyproject.toml

**Decision Needed**: Should we add `markdownify` as a dependency?

### Workflow

```
1. User/Agent calls: web_browse("https://example.com")
   ↓
2. Fetch HTML using requests.get(url)
   ↓
3. Convert HTML → Markdown using markdownify()
   ↓
4. Truncate if too long (prevent token overflow)
   ↓
5. Return markdown string to agent
```

### Error Handling

**Pattern**: Return error strings (never raise exceptions)

**Error Cases**:
- Invalid URL format → "Error: Invalid URL format - must start with http:// or https://"
- HTTP errors (404, 500, etc.) → "Error: HTTP {status_code} - Failed to fetch URL"
- Network timeout → "Error: Request timed out after 30 seconds"
- Connection errors → "Error: Failed to connect to URL"
- Parse errors → "Error: Failed to parse HTML content"

## Tool Signature

```python
@tool
def web_browse(url: str) -> str:
    """Browse a website and return content as Markdown.

    Fetches the URL directly and converts HTML to Markdown format
    for easy reading by the agent. No external APIs required.

    Args:
        url: The URL to browse (must start with http:// or https://)

    Returns:
        Markdown-formatted content from the webpage, or error message if failed
    """
```

## Dependencies Analysis

### Current Dependencies (pyproject.toml)

```toml
dependencies = [
    "openai>=1.0",
    "pytest>=8.0",
    "pre-commit>=4.0",
    "python-dotenv>=1.0",
    "requests>=2.31.0",  # ✅ ALREADY INCLUDED
]
```

### Required Dependencies

**Option 1: Add markdownify to dependencies (RECOMMENDED)**

```toml
dependencies = [
    "openai>=1.0",
    "pytest>=8.0",
    "pre-commit>=4.0",
    "python-dotenv>=1.0",
    "requests>=2.31.0",
    "markdownify>=0.11.0",  # ← ADD THIS
]
```

**Pros**:
- Clean markdown conversion (handles edge cases)
- Well-maintained library
- Minimal footprint (~50KB)
- Standard solution for HTML→Markdown

**Cons**:
- Adds new dependency

**Option 2: Use stdlib html.parser (NOT RECOMMENDED for this use case)**

**Pros**:
- No new dependency

**Cons**:
- Need to write custom markdown conversion logic
- More code to maintain
- Won't handle complex HTML as well
- Reinventing the wheel

### Recommendation

**Add `markdownify` as a dependency** - it's the right tool for the job.

## File Structure

### Files to Create

1. **`tinyagent/tools/builtin/web_browse.py`**
   - Main tool implementation
   - Uses `@tool` decorator
   - Fetches with `requests`
   - Converts with `markdownify`

2. **`examples/web_browse_demo.py`**
   - Example usage with ReactAgent
   - Interactive demo

3. **`tests/api_test/test_web_browse.py`**
   - Unit tests for tool
   - Integration tests with ReactAgent

### Files to Modify

1. **`pyproject.toml`**
   - Add `markdownify>=0.11.0` to dependencies

2. **`tinyagent/tools/builtin/__init__.py`**
   - Export `web_browse` function

3. **`documentation/modules/tools.md`**
   - Document the new tool

## Tool Behavior Specification

### Input Validation

**Valid inputs**:
- `"https://example.com"`
- `"http://example.com"`
- `"https://example.com/path?query=value"`

**Invalid inputs** (return error):
- `"example.com"` (missing protocol)
- `"ftp://example.com"` (wrong protocol)
- `""` (empty string)
- `"not-a-url"` (invalid format)

### HTTP Handling

**Timeouts**: 30 seconds default

**Redirects**: Follow automatically (requests default behavior)

**User-Agent**: Set to `"tinyAgent/1.0"` or similar

**Status Codes**:
- 200 → Process content
- 3xx → Follow redirects (automatic)
- 4xx/5xx → Return error message

### Content Processing

**HTML → Markdown Conversion**:
- Use `markdownify.markdownify(html)` function
- Strip scripts, styles automatically (markdownify handles this)
- Preserve: headings, paragraphs, links, lists, tables, code blocks
- Remove: navigation, ads, metadata (as much as possible)

**Content Truncation**:
- Maximum length: 10,000 characters (~2,500 tokens)
- If longer: truncate and add notice
- Notice: `"\n\n[Content truncated - showing first 10,000 characters]"`

**Empty Content**:
- If markdown is empty after conversion: return error
- Error: `"Error: No readable content found on page"`

## Integration Points

### ReactAgent Integration

**Tool registration**:
```python
from tinyagent import ReactAgent
from tinyagent.tools import web_browse

agent = ReactAgent(tools=[web_browse])
```

**System prompt** (auto-generated):
```
- web_browse: Browse a website and return content as Markdown. | args=(url: str) -> str
```

**Example agent usage**:
```python
result = agent.run(
    "Browse https://example.com and summarize the main content",
    max_steps=3
)
```

### Tool Composition

**Can combine with other tools**:
```python
from tinyagent.tools import web_browse, web_search

# Search for URLs, then browse them
agent = ReactAgent(tools=[web_search, web_browse])

agent.run(
    "Search for Python tutorials, then browse the top result and summarize it"
)
```

## Example Usage Patterns

### Pattern 1: Direct Tool Call

```python
from tinyagent.tools import web_browse

content = web_browse("https://example.com")
print(content)
```

### Pattern 2: With ReactAgent

```python
from tinyagent import ReactAgent
from tinyagent.tools import web_browse

agent = ReactAgent(tools=[web_browse])

result = agent.run(
    "What is on the example.com homepage?",
    max_steps=2
)
```

### Pattern 3: Multi-Step Browsing

```python
agent.run(
    "Browse https://news.ycombinator.com and tell me the top 3 story headlines",
    max_steps=3
)
```

## Testing Strategy

### Unit Tests

**Test cases**:
1. Valid URL returns markdown string
2. Invalid URL format returns error
3. HTTP error (404) returns error message
4. Network timeout returns error message
5. Empty/minimal HTML returns appropriate content or error
6. Very long content gets truncated

### Integration Tests

**Test cases**:
1. ReactAgent can use web_browse tool
2. Tool appears in agent's tool map
3. Agent can successfully browse and summarize content
4. Error handling works in agent context

### Manual Testing

**Test URLs**:
- `https://example.com` - Simple, reliable test page
- `https://github.com` - Complex, real-world site
- `http://httpstat.us/404` - Test 404 handling
- `http://httpstat.us/500` - Test 500 handling

## Configuration Options

### Current Specification

**No configuration needed** - tool should work out of the box.

### Future Enhancements (Not in Initial Version)

- Custom timeout parameter
- Custom User-Agent
- Header customization
- Authentication support (Basic Auth, Bearer tokens)
- Cookie handling
- JavaScript rendering (would require Selenium/Playwright)

## Security Considerations

### SSRF (Server-Side Request Forgery) Protection

**Current approach**: None (trust user input)

**Potential risks**:
- Agent could be tricked into accessing internal URLs
- Local file access via `file://` protocol

**Mitigation options** (future):
- Whitelist/blacklist domains
- Block private IP ranges (127.0.0.1, 192.168.x.x, etc.)
- Validate protocol (only http/https)

**Decision**: Start simple, add protections if needed

### Rate Limiting

**Current approach**: None

**Potential issues**:
- Agent could spam requests to a website
- Could get IP banned

**Mitigation**: Agent-level rate limiting (not tool-level)

## Open Questions

### 1. Should markdownify be a required dependency?

**Options**:
- A) Add to `dependencies` (always installed)
- B) Add to `extras` (optional feature)
- C) Don't add, document as optional

**Recommendation**: Option A - makes the tool always available

### 2. What should the content length limit be?

**Options**:
- A) 10,000 characters (~2,500 tokens)
- B) 20,000 characters (~5,000 tokens)
- C) Configurable parameter

**Recommendation**: Option A - conservative, prevents context overflow

### 3. Should we strip certain HTML elements?

**Examples**: navigation, footer, ads, comments

**Options**:
- A) Let markdownify handle it (default behavior)
- B) Pre-process HTML to remove common junk selectors
- C) Make it configurable

**Recommendation**: Option A - keep it simple initially

### 4. What about JavaScript-heavy sites?

**Problem**: Many modern sites render content with JavaScript

**Options**:
- A) Document limitation (no JS support)
- B) Add Selenium/Playwright support (heavy dependency)
- C) Hybrid approach (fallback to Jina Reader for JS sites)

**Recommendation**: Option A - document limitation

## Success Criteria

### Minimum Viable Tool

The tool is successful if it can:
- ✅ Fetch HTML from valid URLs
- ✅ Convert HTML to readable Markdown
- ✅ Handle errors gracefully (return strings, not exceptions)
- ✅ Work with ReactAgent in reasoning loops
- ✅ Process at least simple/medium complexity websites

### Known Limitations (Acceptable)

- ❌ Does not execute JavaScript
- ❌ May not handle heavily obfuscated HTML well
- ❌ No rate limiting (agent's responsibility)
- ❌ No caching (agent's responsibility)

## Implementation Checklist

### Phase 1: Core Implementation

- [ ] Add `markdownify` to `pyproject.toml` dependencies
- [ ] Create `tinyagent/tools/builtin/web_browse.py`
- [ ] Implement `@tool def web_browse(url: str) -> str`
- [ ] Add input validation (URL format)
- [ ] Add HTTP fetching with `requests`
- [ ] Add HTML→Markdown conversion with `markdownify`
- [ ] Add content truncation
- [ ] Add error handling (all return strings)

### Phase 2: Integration

- [ ] Export from `tinyagent/tools/builtin/__init__.py`
- [ ] Verify export in `tinyagent/tools/__init__.py`

### Phase 3: Testing

- [ ] Create `tests/api_test/test_web_browse.py`
- [ ] Write unit tests (valid URL, invalid URL, errors)
- [ ] Write integration tests (ReactAgent usage)
- [ ] Run full test suite: `pytest tests/api_test/test_web_browse.py -v`

### Phase 4: Documentation & Examples

- [ ] Create `examples/web_browse_demo.py`
- [ ] Update `documentation/modules/tools.md`
- [ ] Add docstring examples

### Phase 5: Code Quality

- [ ] Run `ruff check . --fix`
- [ ] Run `ruff format .`
- [ ] Run `pre-commit run --all-files`
- [ ] Verify all tests pass

### Phase 6: Commit

- [ ] Git add files
- [ ] Commit with message following project conventions
- [ ] Update `.claude` knowledge base if needed

## References

### Documentation
- markdownify: https://github.com/matthewwithanm/python-markdownify
- requests: https://requests.readthedocs.io/

### Similar Implementations
- `tinyagent/tools/builtin/web_search.py` - Error handling pattern
- `examples/jina_reader_demo.py` - URL fetching pattern

### Relevant Files
- `tinyagent/core/registry.py` - Tool decorator
- `tinyagent/agents/react.py` - Agent integration
- `pyproject.toml` - Dependency management

## Next Steps

1. **Review this specification** - Confirm approach is correct
2. **Add markdownify dependency** - Update pyproject.toml
3. **Implement the tool** - Create web_browse.py
4. **Write tests** - Ensure it works correctly
5. **Create examples** - Show how to use it
6. **Document** - Update tools documentation
