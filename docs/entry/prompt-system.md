---
title: Prompt System
path: tinyagent/prompts/
type: directory
depth: 2
description: System prompt templates and loading utilities
exports:
  - SYSTEM
  - CODE_SYSTEM
  - BAD_JSON
  - load_prompt_from_file
  - get_prompt_fallback
seams: [E]
---

# Prompt System

Template-based system prompt management with file loading and fallback support.

## Architecture

```
Prompt System
├── Templates (hardcoded defaults)
│   ├── SYSTEM - ReAct tool-calling prompt
│   ├── CODE_SYSTEM - Python execution prompt
│   └── BAD_JSON - Retry prompt for JSON failures
└── Loaders
    ├── load_prompt_from_file - File loader
    └── get_prompt_fallback - Fallback-aware loader
```

## System Prompts

### SYSTEM

Default prompt for tool-using ReAct agents.

**Purpose:** Guide agents in JSON-based tool calling with structured responses.

**Key Components:**
```python
SYSTEM = """
<role>
You are a helpful assistant with access to tools.
</role>

<critical_rules>
1. Always respond with valid JSON
2. Use the "scratchpad" field for reasoning
3. Call tools using "tool" and "arguments" fields
4. Provide final answer in "answer" field
</critical_rules>

<response_format>
{{
  "scratchpad": "your reasoning here",
  "tool": "tool_name",
  "arguments": {{"param": "value"}}
}}
</response_format>

<example>
User: What's the weather in Tokyo?

{{
  "scratchpad": "User wants weather for Tokyo, I should use the search tool",
  "tool": "web_search",
  "arguments": {{"query": "weather Tokyo"}}
}}

{{
  "scratchpad": "Got the weather data, now I can answer",
  "answer": "The weather in Tokyo is sunny and 72°F."
}}
</example>
"""
```

**Features:**
- XML-like tagging for structure
- JSON response format enforcement
- Tool calling examples
- Scratchpad for reasoning
- Dynamic tool injection via `{tools}` placeholder

### CODE_SYSTEM

Prompt for Python code execution agents.

**Purpose:** Guide agents to solve problems by writing and executing Python code.

**Key Components:**
```python
CODE_SYSTEM = """
<role>
You are a Python code executor. Solve problems by writing code.
</role>

<critical_rules>
1. Write a single Python code block
2. Use available tools and helper functions
3. Call final_answer() when done
4. Use signals for cognitive communication
</critical_rules>

<available_tools>
{tools}
</available_tools>

<available_helpers>
{helpers}
</available_helpers>

<signals>
- uncertain(message): Signal uncertainty
- explore(message): Signal exploration
- commit(message): Signal confidence
</signals>

<response_format>
```python
# Your reasoning and code here
result = calculate()
final_answer(result)
```
</response_format>

<example>
User: Calculate the mean of [1, 2, 3, 4, 5]

```python
data = [1, 2, 3, 4, 5]
mean = sum(data) / len(data)
final_answer(f"The mean is {mean}")
```
</example>
"""
```

**Features:**
- Code block format requirement
- Tool and helper injection
- Signal usage guidance
- `final_answer()` requirement
- Dynamic content placeholders

### BAD_JSON

Retry prompt when agent produces invalid JSON.

**Purpose:** Provide examples and guidance for correct JSON format.

**Key Components:**
```python
BAD_JSON = """
<error>
Your previous response was not valid JSON.
Please ensure your response follows this exact format:
</error>

<correct_format>
{{
  "scratchpad": "your reasoning",
  "tool": "tool_name",
  "arguments": {{"param": "value"}}
}}
</correct_format>

<examples>
Example 1 - Tool call:
{{
  "scratchpad": "I need to search",
  "tool": "web_search",
  "arguments": {{"query": "weather"}}
}}

Example 2 - Final answer:
{{
  "scratchpad": "I have the information",
  "answer": "The answer is 42"
}}
</examples>

<retry>
Please try again with valid JSON.
</retry>
"""
```

**Features:**
- Clear error explanation
- Format examples
- Retry encouragement
- Common mistakes addressed

## Prompt Loaders

### load_prompt_from_file

Load prompt from external file with validation.

**Function Signature:**
```python
def load_prompt_from_file(file_path: str) -> str:
    """
    Load prompt from file with validation.

    Args:
        file_path: Path to prompt file

    Returns:
        Prompt content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file extension not supported
    """
```

**Supported Extensions:**
- `.txt` - Plain text
- `.md` - Markdown
- `.prompt` - Prompt format
- `.xml` - XML format

**Usage Example:**
```python
from tinyagent.prompts import load_prompt_from_file

prompt = load_prompt_from_file("prompts/custom_agent.md")
```

**Validation:**
```python
# File must exist
if not os.path.exists(file_path):
    raise FileNotFoundError(f"Prompt file not found: {file_path}")

# Must be a file
if not os.path.isfile(file_path):
    raise ValueError(f"Path is not a file: {file_path}")

# Extension must be supported
valid_extensions = {".txt", ".md", ".prompt", ".xml"}
ext = os.path.splitext(file_path)[1]
if ext not in valid_extensions:
    raise ValueError(f"Unsupported file extension: {ext}")
```

### get_prompt_fallback

Load prompt from file with automatic fallback to default.

**Function Signature:**
```python
def get_prompt_fallback(
    file_path: str | None,
    default_prompt: str
) -> str:
    """
    Load prompt from file with fallback.

    Args:
        file_path: Optional path to custom prompt
        default_prompt: Fallback prompt if file fails

    Returns:
        Prompt content from file or default
    """
```

**Usage Example:**
```python
from tinyagent.prompts import get_prompt_fallback, SYSTEM

# Try custom file, fall back to default
prompt = get_prompt_fallback(
    "prompts/custom.md",
    default_prompt=SYSTEM
)
```

**Fallback Logic:**
```python
def get_prompt_fallback(file_path, default_prompt):
    # No file provided -> use default
    if file_path is None:
        return default_prompt

    # File doesn't exist -> use default
    if not os.path.exists(file_path):
        return default_prompt

    # Invalid extension -> use default
    ext = os.path.splitext(file_path)[1]
    if ext not in {".txt", ".md", ".prompt", ".xml"}:
        return default_prompt

    # File is empty -> use default
    content = load_prompt_from_file(file_path)
    if not content.strip():
        return default_prompt

    # All checks passed -> use file content
    return content
```

## Dynamic Content Injection

Prompts support placeholders for dynamic content:

### {tools} Placeholder

Inject available tools into prompt:

```python
prompt = SYSTEM.format(tools="""
Available tools:
- search(query): Search the web
- calculate(x, y): Add two numbers
""")
```

### {helpers} Placeholder

Inject helper functions into code prompt:

```python
prompt = CODE_SYSTEM.format(
    tools="",
    helpers="""
Helper functions:
- memory.store(key, value): Store data
- memory.recall(key): Retrieve data
- uncertain(msg): Signal uncertainty
"""
)
```

## Custom Prompt Files

### Creating Custom Prompts

Create a file like `prompts/custom_agent.md`:

```markdown
# Custom Agent Prompt

<role>
You are a specialized data analysis assistant.
</role>

<instructions>
1. Always use pandas for data operations
2. Provide clear visualizations
3. Explain your methodology
4. Include code comments
</instructions>

<tools>
{tools}
</tools>

<output_format>
Provide results in markdown with:
- Methodology explanation
- Code used
- Results summary
- Recommendations
</output_format>
```

### Using Custom Prompts

```python
from tinyagent import ReactAgent

agent = ReactAgent(
    prompt_file="prompts/custom_agent.md",
    tools=[my_tools]
)
```

### Custom Code Execution Prompt

Create `prompts/code_analyzer.md`:

```markdown
# Code Analysis Agent

<role>
You are a code analysis expert. Analyze code quality and suggest improvements.
</role>

<process>
1. Read and understand the code
2. Identify issues and improvements
3. Provide specific recommendations
4. Use tools to run analysis
5. final_answer with summary
</process>

<available_tools>
{tools}
</available_tools>

<output_format>
## Analysis Summary
[Brief overview]

## Issues Found
- Issue 1: description
- Issue 2: description

## Recommendations
- Recommendation 1: description
- Recommendation 2: description

## Code Examples
```python
# Improved code example
```
</output_format>
```

## Prompt Best Practices

### Structure

1. **Clear role definition**
   ```xml
   <role>
   You are a helpful assistant specialized in X.
   </role>
   ```

2. **Critical rules section**
   ```xml
   <critical_rules>
   1. Always do X
   2. Never do Y
   3. Use this format
   </critical_rules>
   ```

3. **Response format examples**
   ```xml
   <response_format>
   {{ "field": "value" }}
   </response_format>
   ```

4. **Concrete examples**
   ```xml
   <example>
   User: question
   {{ "response": "answer" }}
   </example>
   ```

### Content

1. **Be specific** about expected behavior
2. **Provide examples** of correct usage
3. **Use placeholders** for dynamic content
4. **Include error handling** guidance
5. **Define output format** clearly

### Format

1. **Use XML tags** for structure
2. **Group related content** together
3. **Keep it concise** but comprehensive
4. **Test with actual LLM calls**

## Integration with Agents

### ReactAgent

```python
from tinyagent import ReactAgent

# Default prompt
agent1 = ReactAgent()

# Custom prompt file
agent2 = ReactAgent(
    prompt_file="prompts/custom.md"
)

# Custom prompt string
agent3 = ReactAgent(
    system_prompt="Custom prompt here"
)
```

### TinyCodeAgent

```python
from tinyagent import TinyCodeAgent

# Default prompt
agent1 = TinyCodeAgent()

# Custom prompt file
agent2 = TinyCodeAgent(
    prompt_file="prompts/code_custom.md"
)

# System suffix (appended to default)
agent3 = TinyCodeAgent(
    system_suffix="Always include error handling."
)
```

## Prompt Testing

### Test Framework

```python
def test_prompt_formatting():
    """Test prompt produces valid responses."""
    agent = ReactAgent(prompt_file="test_prompt.md")
    result = agent.run_sync("Test question")
    assert "expected content" in result

def test_prompt_injection():
    """Test dynamic content injection."""
    prompt = SYSTEM.format(tools="Test tools")
    assert "Test tools" in prompt

def test_prompt_fallback():
    """Test fallback mechanism."""
    prompt = get_prompt_fallback(
        "nonexistent.md",
        default_prompt=SYSTEM
    )
    assert prompt == SYSTEM
```

### Validation

```python
def validate_prompt(prompt: str) -> bool:
    """Validate prompt has required sections."""
    required_tags = ["<role>", "<critical_rules>"]
    return all(tag in prompt for tag in required_tags)
```

## Debugging

### Enable Prompt Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)

agent = ReactAgent(verbose=True)
# Logs will show full prompt sent to LLM
```

### Inspect Generated Prompt

```python
from tinyagent.prompts import get_prompt_fallback, SYSTEM

prompt = get_prompt_fallback(
    "custom.md",
    default_prompt=SYSTEM
)

# Print to inspect
print(prompt)
```

### Common Issues

**Placeholders not replaced:**
```python
# Error
prompt = SYSTEM  # {tools} still in prompt

# Fix
prompt = SYSTEM.format(tools="Available tools...")
```

**File not found:**
```python
# Falls back to default
prompt = get_prompt_fallback(
    "missing.md",
    default_prompt=SYSTEM
)
# Returns SYSTEM
```

**Empty file:**
```python
# Falls back to default
prompt = get_prompt_fallback(
    "empty.md",
    default_prompt=SYSTEM
)
# Returns SYSTEM (file empty)
```

## Advanced Usage

### Conditional Prompts

```python
def get_prompt(model_name: str) -> str:
    """Select prompt based on model."""
    if "gpt-4" in model_name:
        return load_prompt_from_file("prompts/gpt4.md")
    else:
        return load_prompt_from_file("prompts/default.md")

agent = ReactAgent(
    model="gpt-4o",
    system_prompt=get_prompt("gpt-4o")
)
```

### Prompt Chaining

```python
base_prompt = load_prompt_from_file("base.md")
task_specific = load_prompt_from_file("analysis.md")

combined = f"{base_prompt}\n\n{task_specific}"
agent = ReactAgent(system_prompt=combined)
```

### Dynamic Prompt Construction

```python
def build_prompt(tools, instructions, examples):
    """Build prompt from components."""
    return f"""
    <role>You are a helpful assistant.</role>

    <tools>{tools}</tools>

    <instructions>{instructions}</instructions>

    <examples>{examples}</examples>
    """

prompt = build_prompt(
    tools="search, calculate",
    instructions="Always show your work",
    examples="..."
)
```
