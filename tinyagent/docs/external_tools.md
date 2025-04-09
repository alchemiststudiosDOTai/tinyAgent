# External Tools for tinyAgent

This guide explains how to implement tools for tinyAgent using languages other than Python, focusing on the cross-language integration capabilities of the framework. tinyAgent's JSON-based architecture makes it language-agnostic, allowing tools to be implemented in any language that can process JSON.

## JSON Communication Protocol

External tools communicate with tinyAgent through a standardized JSON protocol:

1. **Input**: The tool receives a JSON object through stdin containing the tool parameters
2. **Processing**: The tool processes the input and generates a result
3. **Output**: The tool returns a JSON object through stdout containing the result

This protocol allows any language that can read from stdin and write to stdout to implement tools for tinyAgent, creating a universal interface for cross-language integration.

## Creating a Manifest File

External tools require a `manifest.json` file that defines the tool's metadata:

```json
{
  "name": "tool_name",
  "description": "Clear description of what the tool does",
  "parameters": {
    "param1": {
      "type": "string",
      "description": "Description of parameter",
      "required": true
    },
    "param2": {
      "type": "float",
      "description": "Description of parameter",
      "default": 0.0
    },
    "param3": {
      "type": "integer",
      "description": "Description of parameter",
      "required": false
    }
  },
  "executable": "executable_name",
  "working_directory": "./relative/path",
  "rate_limit": 10
}
```

The fields in the manifest are:

- `name`: The tool name (lowercase, no spaces)
- `description`: A clear description of what the tool does
- `parameters`: A dictionary mapping parameter names to their specifications
- `executable`: The name of the executable file in the tool's directory
- `working_directory`: (Optional) Relative path to the working directory
- `rate_limit`: (Optional) Maximum calls allowed per session

Parameter specifications can include:
- `type`: The data type (`string`, `float`, `integer`, or `any`)
- `description`: Description of the parameter
- `required`: Whether the parameter is required (default: true)
- `default`: Default value if parameter is not provided

The executable file should be in the same directory as the manifest and should have executable permissions (`chmod +x` on Unix-based systems).

## Directory Structure

External tools should be organized in a directory structure like this:

```
external_tools/
  ├── text_rank/
  │   ├── manifest.json
  │   ├── text_rank       # Compiled C executable
  │   └── text_rank.c     # Source code
  ├── go_calculator/
  │   ├── manifest.json
  │   ├── calculator      # Compiled Go executable
  │   └── calculator.go   # Source code
  └── bash_file_search/
      ├── manifest.json
      └── file_search.sh  # Bash script with executable permissions
```

## Integration with Factory System

When external tools are loaded, they're automatically registered with the AgentFactory:

```python
from core.tools import load_external_tools
from core.factory.agent_factory import AgentFactory

# Get the singleton factory instance
factory = AgentFactory.get_instance()

# Load external tools from a directory
external_tools = load_external_tools("/path/to/external_tools")

# Register with the factory
for tool in external_tools:
    factory.register_tool(tool)

# Create an agent that will use these tools
agent = Agent(factory=factory)
```

All tool calls are routed through the factory to ensure proper tracking and rate limiting, regardless of the language the tool is implemented in.

## Language-Specific Implementations

### C/C++ Implementation

C and C++ are ideal for performance-critical tools or when integrating with existing C/C++ libraries:

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <json-c/json.h>

int main() {
    char buffer[4096];
    
    // Read JSON from stdin
    fgets(buffer, sizeof(buffer), stdin);
    
    // Parse input JSON
    struct json_object *input_json = json_tokener_parse(buffer);
    
    // Extract parameters
    struct json_object *text_obj, *num_sentences_obj;
    json_object_object_get_ex(input_json, "text", &text_obj);
    json_object_object_get_ex(input_json, "num_sentences", &num_sentences_obj);
    
    const char *text = json_object_get_string(text_obj);
    int num_sentences = json_object_get_int(num_sentences_obj);
    
    // Process text using your algorithm
    // ... (implementation of text processing)
    
    // Create result JSON
    struct json_object *result_json = json_object_new_object();
    struct json_object *sentences_array = json_object_new_array();
    
    // Add extracted sentences to array
    for (int i = 0; i < num_sentences; i++) {
        // Example - in real code, you'd use your algorithm's results
        char sentence[100];
        sprintf(sentence, "This is extracted sentence %d", i+1);
        json_object_array_add(sentences_array, json_object_new_string(sentence));
    }
    
    json_object_object_add(result_json, "sentences", sentences_array);
    
    // Output result JSON
    printf("%s\n", json_object_to_json_string(result_json));
    
    // Cleanup
    json_object_put(input_json);
    json_object_put(result_json);
    
    return 0;
}
```

### Go Tools Implementation

Go is an excellent choice for implementing tinyAgent tools due to its strong typing, efficient JSON handling, and ability to compile to standalone executables:

```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
)

// Define input structure
type CalculatorInput struct {
    Operation string  `json:"operation"`
    Num1      float64 `json:"num1"`
    Num2      float64 `json:"num2"`
}

// Define output structure
type CalculatorOutput struct {
    Result    float64 `json:"result"`
    Operation string  `json:"operation"`
    Num1      float64 `json:"num1"`
    Num2      float64 `json:"num2"`
}

// Define error output structure
type CalculatorError struct {
    Error string `json:"error"`
}

func main() {
    // Read JSON from stdin
    var input CalculatorInput
    if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
        outputError(fmt.Sprintf("Failed to parse input: %v", err))
        return
    }

    // Process the calculation
    result, err := calculate(input)
    if err != nil {
        outputError(err.Error())
        return
    }

    // Output the result
    output := CalculatorOutput{
        Result:    result,
        Operation: input.Operation,
        Num1:      input.Num1,
        Num2:      input.Num2,
    }
    json.NewEncoder(os.Stdout).Encode(output)
}

func calculate(input CalculatorInput) (float64, error) {
    switch input.Operation {
    case "add":
        return input.Num1 + input.Num2, nil
    case "subtract":
        return input.Num1 - input.Num2, nil
    case "multiply":
        return input.Num1 * input.Num2, nil
    case "divide":
        if input.Num2 == 0 {
            return 0, fmt.Errorf("division by zero")
        }
        return input.Num1 / input.Num2, nil
    default:
        return 0, fmt.Errorf("unknown operation: %s", input.Operation)
    }
}

func outputError(message string) {
    error := CalculatorError{
        Error: message,
    }
    json.NewEncoder(os.Stdout).Encode(error)
}
```

### Rust Implementation

Rust provides memory safety with C-like performance, making it excellent for high-performance tools:

```rust
use serde::{Deserialize, Serialize};
use std::io::{self, Read};

#[derive(Deserialize)]
struct Input {
    text: String,
    num_sentences: Option<usize>,
}

#[derive(Serialize)]
struct Output {
    sentences: Vec<String>,
}

#[derive(Serialize)]
struct ErrorOutput {
    error: String,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Read JSON from stdin
    let mut buffer = String::new();
    io::stdin().read_to_string(&mut buffer)?;
    
    // Parse input
    let input: Input = match serde_json::from_str(&buffer) {
        Ok(input) => input,
        Err(e) => {
            let error = ErrorOutput {
                error: format!("Failed to parse input: {}", e),
            };
            println!("{}", serde_json::to_string(&error)?);
            return Ok(());
        }
    };
    
    let num_sentences = input.num_sentences.unwrap_or(3);
    
    // Process text - this would use your actual algorithm
    let sentences = match extract_key_sentences(&input.text, num_sentences) {
        Ok(sentences) => sentences,
        Err(e) => {
            let error = ErrorOutput {
                error: format!("Processing error: {}", e),
            };
            println!("{}", serde_json::to_string(&error)?);
            return Ok(());
        }
    };
    
    // Create and output result
    let output = Output { sentences };
    println!("{}", serde_json::to_string(&output)?);
    
    Ok(())
}

fn extract_key_sentences(text: &str, count: usize) -> Result<Vec<String>, String> {
    // This is where your TextRank or other algorithm would be implemented
    // Just a placeholder implementation for the example
    let sentences: Vec<String> = text
        .split('.')
        .take(count)
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();
    
    if sentences.is_empty() {
        return Err("No sentences found in text".to_string());
    }
    
    Ok(sentences)
}
```

### Bash Tools Implementation

Bash is ideal for tools that primarily wrap existing command-line utilities or perform system operations:

```bash
#!/bin/bash

# File search tool for tinyAgent
# Requires: jq, find

# Set error handling
set -e
trap 'echo "{\"error\": \"Script failed unexpectedly: $BASH_COMMAND\"}"; exit 1' ERR

# Read JSON input from stdin
input=$(cat)

# Parse JSON parameters
directory=$(echo "$input" | jq -r '.directory // ""')
pattern=$(echo "$input" | jq -r '.pattern // ""')
max_depth=$(echo "$input" | jq -r '.max_depth // "3"')
type=$(echo "$input" | jq -r '.type // "f"')

# Validate required parameters
if [[ -z "$directory" ]]; then
    echo '{"error": "directory parameter is required"}'
    exit 1
fi

if [[ -z "$pattern" ]]; then
    echo '{"error": "pattern parameter is required"}'
    exit 1
fi

# Validate directory exists
if [[ ! -d "$directory" ]]; then
    echo "{\"error\": \"Directory not found: $directory\"}"
    exit 1
fi

# Execute find command
if ! result=$(find "$directory" -maxdepth "$max_depth" -type "$type" -name "$pattern" 2>&1); then
    echo "{\"error\": \"Find command failed: $result\"}"
    exit 1
fi

# Convert result to JSON array
files_json=$(find "$directory" -maxdepth "$max_depth" -type "$type" -name "$pattern" -print0 | 
             xargs -0 -I{} echo "{}" | 
             jq -R -s 'split("\n") | map(select(length > 0))')

# Build and output the final JSON result
echo "$input" | jq --argjson files "$files_json" '{
    result: "success",
    directory: .directory,
    pattern: .pattern,
    max_depth: (.max_depth // 3),
    type: (.type // "f"),
    count: ($files | length),
    files: $files
}'
```

## Performance Considerations

When implementing tools in different languages, consider these performance aspects:

### Process Startup Overhead

External tools incur process startup overhead. For frequently used tools, consider:
- Implementing in Python directly if performance isn't critical
- Using persistent processes for high-frequency tools
- Batching operations to minimize process creation

### Memory Usage

Different languages have different memory characteristics:
- C/C++ provide fine-grained memory control but require manual management
- Rust ensures memory safety with minimal overhead
- Go has a garbage collector with good performance characteristics
- JVM languages (Java, Kotlin, Scala) may have higher memory requirements

### Execution Speed

Consider language advantages:
- C/C++ for compute-intensive operations without external dependencies
- Rust for memory-safe performance-critical code
- Go for good balance of development speed and runtime performance
- JavaScript/TypeScript for integration with web technologies
- Python for rapid development when performance isn't critical

## Error Handling Best Practices

Proper error handling is essential for tools in any language:

1. **Validate Input First**: Check all parameters before processing
2. **Structured Error Responses**: Return errors in the expected JSON format
3. **Descriptive Messages**: Provide clear error messages explaining what went wrong
4. **Graceful Degradation**: Try to provide partial results if possible
5. **Resource Cleanup**: Always clean up resources even in error cases

Example error response format:

```json
{
  "error": "Clear description of what went wrong",
  "code": "optional_error_code",
  "details": {
    "param": "problematic_parameter",
    "valid_values": ["list", "of", "valid", "values"]
  }
}
```

## Testing External Tools

### Manual Testing

Test your tools by piping JSON input:

```bash
echo '{"operation": "add", "num1": 5, "num2": 3}' | ./calculator
```

### Automated Testing

Create test scripts to verify tool behavior:

```bash
#!/bin/bash
# test_calculator.sh

declare -a tests=(
    '{"operation": "add", "num1": 5, "num2": 3}'
    '{"operation": "subtract", "num1": 10, "num2": 4}'
    '{"operation": "multiply", "num1": 3, "num2": 7}'
    '{"operation": "divide", "num1": 15, "num2": 3}'
    '{"operation": "divide", "num1": 10, "num2": 0}'  # Error case
)

for test in "${tests[@]}"; do
    echo "Test input: $test"
    result=$(echo "$test" | ./calculator)
    echo "Result: $result"
    echo "---"
done
```

### Debugging

Add logging to help debug your tools:

```go
// Go logging
func logDebug(message string) {
    f, _ := os.OpenFile("/tmp/tool_debug.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
    defer f.Close()
    fmt.Fprintf(f, "[%s] %s\n", time.Now().Format(time.RFC3339), message)
}
```

```bash
# Bash logging
DEBUG=true

debug() {
    if [[ "$DEBUG" == "true" ]]; then
        echo "[DEBUG] $1" >> /tmp/tool_debug.log
    fi
}
```

## Security Considerations

External tools introduce security considerations:

1. **Input Sanitization**: Always sanitize inputs to prevent injection attacks
2. **Permission Boundaries**: Use the principle of least privilege
3. **Resource Limits**: Implement timeouts and resource constraints
4. **Error Information**: Avoid leaking sensitive information in error messages
5. **Dependency Management**: Keep dependencies updated to avoid vulnerabilities

## Best Practices

1. **Focus on Single Responsibility**: Each tool should do one thing well
2. **Clear Documentation**: Document parameters, return values, and error conditions
3. **Consistent JSON Structure**: Maintain consistent input/output formats
4. **Error Handling**: Provide meaningful error messages
5. **Resource Management**: Clean up resources properly
6. **Performance Optimization**: Consider startup time and processing efficiency
7. **Language Appropriateness**: Choose the right language for the task

## Conclusion

The cross-language capability of tinyAgent through JSON-based tool interfaces allows you to:

1. Leverage the optimal language for each task
2. Integrate with existing codebases in any language
3. Use specialized libraries not available in Python
4. Implement performance-critical operations in languages like C, Rust, or Go
5. Create a polyglot agent system with unified interfaces

By following these guidelines, you can create powerful, efficient tools for tinyAgent in various languages, while maintaining compatibility with the tinyAgent factory-based architecture and ensuring proper error handling, security, and performance optimization.
