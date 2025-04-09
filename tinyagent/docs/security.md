# tinyAgent Security Configuration

This document details the security configuration options available in tinyAgent, particularly focused on the code execution capabilities.

## Overview

tinyAgent provides a flexible security model that allows you to balance security with functionality based on your specific needs and trust level. By default, tinyAgent operates in a secure mode that restricts potentially dangerous operations, but these restrictions can be configured through the `config.yml` file.

## Code Execution Security

The `anon_coder` tool, which allows execution of Python code, includes security measures to prevent potentially harmful operations. These security measures can be configured through the `code_execution` section in the `config.yml` file.

### Basic Configuration

```yaml
# Code execution security configuration
code_execution:
  # Allow potentially dangerous operations (file operations, etc)
  allow_dangerous_operations: false  # Set to true to disable security restrictions
```

Setting `allow_dangerous_operations` to `true` will disable the security checks for dangerous operations, allowing the code to perform operations like file access, system operations, and more. This should be used with caution, as it can potentially allow harmful code to be executed.

### Advanced Configuration

For more granular control, you can configure specific types of operations:

```yaml
# Code execution security configuration
code_execution:
  # Allow potentially dangerous operations (file operations, etc)
  allow_dangerous_operations: false
  
  # Optional: more granular control
  allowed_operations:
    file_operations: false  # Allow file operations like open(), read, write
    os_operations: false    # Allow operations using the os module
    imports: ["os", "sys"]  # Additional allowed imports beyond the defaults
```

#### Allowed Operations

- `file_operations`: When set to `true`, allows operations like `open()`, file reading, and file writing
- `os_operations`: When set to `true`, allows operations using the `os` module (e.g., `os.system()`)
- `imports`: A list of additional modules that can be imported beyond the default allowed modules

### Default Allowed Imports

By default, the following imports are allowed regardless of other settings:

```python
allowed_imports = {
    'math', 'random', 'string', 're', 'collections', 'itertools',
    'json', 'datetime', 'statistics', 'functools', 'operator',
    'numpy', 'pandas'
}
```

### Default Restricted Operations

By default, the following operations are restricted unless `allow_dangerous_operations` is set to `true`:

```python
dangerous_operations = [
    r'exec\s*\(',       # Code execution
    r'eval\s*\(',       # Code evaluation
    r'os\.',            # OS module access
    r'sys\.',           # Sys module access
    r'subprocess\.',    # Subprocess access
    r'shutil\.',        # Shutil access
    r'__import__\s*\(',
    r'open\s*\(',       # File operations
    r'globals\s*\(',    # Access to globals
    r'locals\s*\(',     # Access to locals
    r'compile\s*\(',    # Code compilation
    r'builtins\.',      # Access to builtins
]
```

## Use Cases

### Development Environment

For a development environment where you need full access to system resources:

```yaml
code_execution:
  allow_dangerous_operations: true
```

### Web API or Service

For a web API or service exposed to untrusted users:

```yaml
code_execution:
  allow_dangerous_operations: false
  allowed_operations:
    file_operations: false
    os_operations: false
    imports: []
```

### Trusted Environment with Specific Needs

For a trusted environment that needs access to specific operations:

```yaml
code_execution:
  allow_dangerous_operations: false
  allowed_operations:
    file_operations: true  # Allow file operations for data processing
    os_operations: false   # But no system operations
    imports: ["os.path", "pathlib"]  # Allow path manipulation modules
```

## Best Practices

1. **Default to Secure**: Start with `allow_dangerous_operations: false` and only enable specific operations as needed
2. **Least Privilege**: Only enable the minimum permissions necessary for your use case
3. **Isolation**: When possible, run tinyAgent in an isolated environment (e.g., Docker container) for an additional layer of security
4. **Regular Updates**: Ensure you're using the latest version of tinyAgent to benefit from security improvements

## Conclusion

tinyAgent's configurable security model allows you to balance security and functionality based on your specific needs. By carefully configuring these settings, you can ensure that your agent operates securely while still providing the capabilities you need.
