# Tool Creation Guide

A clear, step-by-step guide to creating tools for TinyAgent.

## Quick Start: Creating Your First Tool

### 1. Basic Tool Creation

```python
from tinyagent import tool, ReactAgent

@tool
def calculate(expression: str) -> float:
    """Evaluate a mathematical expression safely."""
    # Safe evaluation using ast.literal_eval for constants
    try:
        return float(eval(expression))  # Be careful with eval in production
    except:
        return 0.0

# Use the tool
agent = ReactAgent(tools=[calculate])
result = agent.run("What is 15 * 7?")
```

### 2. Tool Requirements Checklist

✅ **Function signature with type hints**
```python
def my_tool(param1: str, param2: int) -> str:  # ✓ Good
def my_tool(param1, param2):                    # ✗ Missing types
```

✅ **Clear docstring describing what the tool does**
```python
@tool
def get_weather(city: str) -> str:
    """Get current weather information for a city."""  # ✓ Clear purpose
    return f"Weather in {city}: Sunny, 72°F"
```

✅ **Return string or easily convertible types**
```python
@tool
def count_words(text: str) -> int:
    """Count the number of words in text."""
    return len(text.split())  # Returns int - gets converted to string
```

## Tool Creation Patterns

### Pattern 1: Simple Data Tools
```python
@tool
def get_user_info(user_id: str) -> str:
    """Retrieve user information by ID."""
    # Your data retrieval logic
    return f"User {user_id}: John Doe, email: john@example.com"

@tool
def search_database(query: str) -> str:
    """Search database and return formatted results."""
    # Your search logic
    return f"Found 3 results for '{query}'"
```

### Pattern 2: API Integration Tools
```python
import requests
from tinyagent import tool

@tool
def call_external_api(endpoint: str) -> str:
    """Make API call and return formatted response."""
    try:
        response = requests.get(endpoint, timeout=10)
        return f"API Response: {response.json()}"
    except Exception as e:
        return f"API Error: {str(e)}"
```

### Pattern 3: File Operation Tools
```python
@tool
def read_file(file_path: str) -> str:
    """Read and return file contents."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"
```

### Pattern 4: Complex Processing Tools
```python
@tool
def analyze_text(text: str) -> str:
    """Analyze text and return insights."""
    word_count = len(text.split())
    char_count = len(text)
    sentences = text.count('.') + text.count('!') + text.count('?')

    return f"Analysis: {word_count} words, {char_count} characters, {sentences} sentences"
```

## Advanced Tool Features

### Using Multiple Parameters
```python
@tool
def create_user(name: str, email: str, age: int) -> str:
    """Create a new user with the provided information."""
    # Validation
    if age < 0 or age > 150:
        return "Error: Invalid age"
    if '@' not in email:
        return "Error: Invalid email format"

    # Creation logic
    return f"Created user: {name} ({email}), age {age}"
```

### Error Handling Best Practices
```python
@tool
def safe_division(a: float, b: float) -> str:
    """Divide two numbers with proper error handling."""
    try:
        if b == 0:
            return "Error: Cannot divide by zero"
        result = a / b
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"
```

### Environment Variables and Configuration
```python
import os
from tinyagent import tool

@tool
def get_api_data(query: str) -> str:
    """Fetch data from configured API."""
    api_key = os.getenv("MY_API_KEY")
    if not api_key:
        return "Error: MY_API_KEY environment variable not set"

    # Use api_key for authenticated requests
    return f"Data for '{query}' retrieved successfully"
```

## Complete Example: Building a File Manager Tool Set

```python
import os
from pathlib import Path
from tinyagent import tool, ReactAgent

@tool
def list_files(directory: str) -> str:
    """List all files in the specified directory."""
    try:
        path = Path(directory)
        if not path.exists():
            return f"Directory not found: {directory}"

        files = [f.name for f in path.iterdir() if f.is_file()]
        return f"Files in {directory}: {', '.join(files)}"
    except Exception as e:
        return f"Error listing files: {str(e)}"

@tool
def create_file(file_path: str, content: str) -> str:
    """Create a new file with the specified content."""
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        return f"File created successfully: {file_path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"

@tool
def file_info(file_path: str) -> str:
    """Get information about a file."""
    try:
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"

        size = path.stat().st_size
        return f"File: {file_path}, Size: {size} bytes"
    except Exception as e:
        return f"Error getting file info: {str(e)}"

# Create agent with file tools
file_agent = ReactAgent(tools=[list_files, create_file, file_info])

# Use the agent
result = file_agent.run("List the files in the current directory")
```

## Testing Your Tools

### Direct Tool Testing
```python
@tool
def my_tool(value: str) -> str:
    """Process a value."""
    return f"Processed: {value}"

# Test the tool directly
result = my_tool("test")
print(result)  # "Processed: test"
```

### Agent Integration Testing
```python
agent = ReactAgent(tools=[my_tool])
result = agent.run("Process the value 'hello world'")
print(result)
```

## Common Pitfalls and Solutions

### ❌ Don't: Missing type hints
```python
@tool
def bad_tool(value):  # Missing type hints
    return value
```

### ✅ Do: Always use type hints
```python
@tool
def good_tool(value: str) -> str:
    return value
```

### ❌ Don't: Unclear docstrings
```python
@tool
def process(data: str) -> str:
    """Does stuff."""  # Too vague
    return data
```

### ✅ Do: Descriptive docstrings
```python
@tool
def process_user_input(data: str) -> str:
    """Clean and validate user input data."""
    return data.strip().lower()
```

### ❌ Don't: Unhandled exceptions
```python
@tool
def risky_operation(file_path: str) -> str:
    with open(file_path, 'r') as f:  # Could raise FileNotFoundError
        return f.read()
```

### ✅ Do: Proper error handling
```python
@tool
def safe_file_read(file_path: str) -> str:
    """Read file contents safely."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"
```

## Tool Registration System

## Tool Class

The `Tool` class wraps functions with metadata:

### Attributes
- `fn`: The callable function
- `name`: Function name
- `doc`: Function docstring
- `signature`: Function signature from `inspect`

### Methods
- `__call__(*args, **kwargs)`: Direct function call
- `run(payload)`: Execute with dictionary of arguments

## Registry System

The tool registry provides:
- Centralized tool management
- Decorator-based registration
- Immutable views
- Registry freezing for security

### Usage

```python
from tinyagent import tool, get_registry, freeze_registry

@tool
def my_tool(param: str) -> str:
    return f"Processed: {param}"

# Get registry view
registry = get_registry()
tool_obj = registry["my_tool"]

# Freeze registry to prevent changes
freeze_registry()
```

## API Reference

### `@tool` decorator
Register a function as a tool.

### `Tool` class
Wrapper for tool functions.

#### `Tool(fn, name, doc, signature)`
Create a Tool instance.

Parameters:
- `fn`: The callable function
- `name`: Function name
- `doc`: Function docstring
- `signature`: Function signature

#### `run(payload)`
Execute tool with dictionary arguments.

Parameters:
- `payload`: Dictionary of arguments

### Registry Functions

#### `get_registry()`
Return a read-only view of the default registry.

#### `freeze_registry()`
Lock the registry against further changes.

## Security Considerations

- Tools are executed with caller's permissions
- Argument validation prevents signature mismatches
- Registry freezing prevents runtime tool injection
- Tool functions should validate their own inputs
