# TinyAgent Tools Documentation

This directory contains the core tools for the TinyAgent framework. Each tool is designed to provide specific functionality while maintaining security and efficiency.

## Tool Categories

### Template & Examples

#### `boilerplate_tool.py`
- **Purpose**: Example implementation demonstrating complete tool lifecycle
- **Features**:
  - Parameter validation
  - Rate limiting
  - Error handling
  - Logging integration
  - Documentation standards
  - Example test case
- **Usage Example**:
  ```python
  from core.tools import boilerplate_tool
  
  result = boilerplate_tool.execute(
      input_data="sample text to process",
      max_items=3
  )
  ```

### Code & Development Tools

#### `codeagent_tool.py`
- **Purpose**: AI-powered Python code generation from natural language
- **Features**:
  - Natural language to Python code conversion
  - Built-in safety checks
  - Code optimization suggestions
  - Documentation generation
  - Error handling patterns
- **Inspiration**: Inspired by smolagents library from Hugging Face
- **Usage Example**:
  ```python
  from core.tools import codeagent_tool
  
  result = codeagent_tool.execute(
      task="Create a function that calculates fibonacci sequence",
      context_memory="Previous calculations...",
      mode="advanced",
      available_tools=["web_search", "summarize_text"]
  )
  ```

#### `anon_coder.py`
- **Purpose**: Safe Python code execution environment
- **Features**:
  - Secure code validation
  - Timeout protection
  - Restricted imports
  - Detailed error reporting
  - Configuration-based security settings

#### `aider.py`
- **Purpose**: AI coding assistant integration
- **Features**:
  - Code generation
  - Code modification
  - AI-assisted development

#### `llm_serializer.py`
- **Purpose**: LLM data serialization and handling
- **Features**:
  - Data format conversion
  - LLM response processing
  - Structured data handling

### Search & Information Tools

#### `brave_search.py`
- **Purpose**: Brave search engine integration
- **Features**:
  - Web search capabilities
  - Result processing
  - Query optimization

#### `duckduckgo_search.py`
- **Purpose**: DuckDuckGo search integration
- **Features**:
  - Privacy-focused search
  - Result formatting
  - Query handling

#### `enhanced_deepsearch.py`
- **Purpose**: Advanced search capabilities
- **Features**:
  - Deep content analysis
  - Advanced filtering
  - Result ranking

#### `os_deepsearch.py`
- **Purpose**: Operating system deep search
- **Features**:
  - File system search
  - Content indexing
  - Pattern matching

### File & Content Tools

#### `file_manipulator.py`
- **Purpose**: File operations and management
- **Features**:
  - File creation/modification
  - Directory operations
  - File system utilities

#### `ripgrep.py`
- **Purpose**: Fast text search
- **Features**:
  - Regular expression search
  - Fast pattern matching
  - Result highlighting

#### `content_processor.py`
- **Purpose**: Content processing and analysis
- **Features**:
  - Text processing
  - Content extraction
  - Format conversion

#### `custom_text_browser.py`
- **Purpose**: Text browsing capabilities
- **Features**:
  - Text navigation
  - Content display
  - Interactive browsing

### System & Integration

#### `external.py`
- **Purpose**: External tool loading and management
- **Features**:
  - Dynamic tool loading
  - External tool integration
  - Tool lifecycle management

## Tool Architecture

### Common Features
- Standardized Tool class interface
- Parameter typing support
- Comprehensive error handling
- Security measures
- Logging integration

### Integration Points
- Dynamic tool loading
- Configuration support
- Standardized parameter types
- Common error handling
- Logging system integration

## Security Considerations

All tools implement security measures including:
- Input validation
- Resource limits
- Access controls
- Safe execution environments
- Error containment

## Usage

Tools can be imported and used as follows:

```python
from core.tools import anon_coder_tool, file_manipulator_tool

# Example usage
result = anon_coder_tool.execute(code="print('Hello, World!')")
```

## Adding New Tools

To add a new tool:
1. Create a new Python file in this directory
2. Implement the Tool class interface
3. Add security measures and error handling
4. Register the tool in `__init__.py`
5. Update this documentation

## Configuration

Tools can be configured through the framework's configuration system. See individual tool documentation for specific configuration options.

## Creating New Tools

### Step-by-Step Process

1. **Tool Structure**
   ```python
   from typing import Dict, Any, Optional
   from ..tool import Tool, ParamType
   from ..logging import get_logger
   from ..exceptions import ToolError
   
   class NewTool(Tool):
       def __init__(self):
           super().__init__(
               name="tool_name",
               description="Detailed tool description",
               parameters={
                   "param1": ParamType.STRING,
                   "param2": ParamType.INTEGER
               }
           )
   ```

2. **Required Components**
   - Tool class inheriting from base Tool
   - Proper parameter typing
   - Error handling
   - Logging integration
   - Security measures
   - Documentation

3. **Best Practices**
   - Use type hints
   - Implement comprehensive error handling
   - Add detailed logging
   - Include docstrings
   - Follow security guidelines
   - Add unit tests
   - Update documentation

4. **Integration Steps**
   - Create tool file in `core/tools/`
   - Implement Tool class
   - Add to `__init__.py`
   - Update README.md
   - Add tests
   - Add configuration options

5. **Security Checklist**
   - Input validation
   - Resource limits
   - Access controls
   - Safe execution
   - Error containment
   - Logging
   - Configuration validation

6. **Documentation Requirements**
   - Purpose
   - Features
   - Parameters
   - Return values
   - Examples
   - Security considerations
   - Configuration options

### Example Implementation

```python
class ExampleTool(Tool):
    def __init__(self):
        super().__init__(
            name="example",
            description="Example tool description",
            parameters={
                "input": ParamType.STRING,
                "options": ParamType.DICT
            }
        )
    
    def execute(self, input: str, options: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Implementation
            return {"result": "success"}
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            raise ToolError(f"Failed: {str(e)}")
```

## Case Study: CodeAgent Tool Implementation

The CodeAgent tool demonstrates advanced tool implementation with several key features:

### 1. Advanced Structure
```python
# Use dataclasses for context management
@dataclass
class CodeGenerationContext:
    memory: str = ""
    available_tools: List[str] = None
    mode: CodeGenerationMode = CodeGenerationMode.BASIC
    max_iterations: int = 3
    timeout: int = 15

# Use enums for mode management
class CodeGenerationMode(Enum):
    BASIC = "basic"
    ADVANCED = "advanced"
    RESEARCH = "research"
```

### 2. Security Implementation
```python
def validate_generated_code(code: str) -> bool:
    dangerous_patterns = [
        r'exec\s*\(',
        r'eval\s*\(',
        r'os\.',
        r'sys\.',
        r'subprocess\.',
        r'__import__\s*\(',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            logger.warning(f"Dangerous operation detected: {pattern}")
            return False
```

### 3. Context Management
```python
def generate_system_prompt(context: CodeGenerationContext, task: str) -> str:
    tools_description = "\n".join([
        f"- {tool}() -> returns {tool} results" 
        for tool in context.available_tools
    ])
```

### 4. Error Handling
```python
try:
    # Implementation
    return {
        "success": True,
        "generated_code": generated_code,
        "execution_result": execution_output,
        "error": None
    }
except Exception as e:
    logger.error(f"Error: {str(e)}\n{traceback.format_exc()}")
    return {
        "success": False,
        "error": str(e),
        "generated_code": "",
        "execution_result": ""
    }
```

## Tool Development Guidelines

### 1. Planning Phase
- Define tool purpose and scope
- Identify required parameters
- Plan security measures
- Design error handling
- Consider integration points

### 2. Implementation Phase
- Create tool class structure
- Implement core functionality
- Add security measures
- Implement error handling
- Add logging
- Write documentation

### 3. Testing Phase
- Unit tests
- Integration tests
- Security tests
- Performance tests
- Error handling tests

### 4. Integration Phase
- Add to `__init__.py`
- Update documentation
- Add examples
- Configure logging
- Set up monitoring

### 5. Maintenance Phase
- Monitor usage
- Gather feedback
- Update documentation
- Optimize performance
- Fix bugs
- Add features

## Configuration

Tools can be configured through the framework's configuration system. See individual tool documentation for specific configuration options.
