# Agent Character Test Suite

This directory contains comprehensive character tests for the `tinyagent.agent.Agent` class. These tests are designed to verify the Agent's behavior with various character inputs, edge cases, and challenging scenarios.

## Test Files

### `test_agent_character.py`
Core character handling tests including:
- Empty strings and whitespace
- Unicode characters and emojis
- Special characters and control characters
- Very long strings
- Mixed character sets and scripts
- Memory pressure testing
- Caching behavior with character data

### `test_agent_parsing_edge_cases.py`
JSON parsing and response validation tests including:
- Malformed JSON with various character issues
- Unicode escape sequences
- Deeply nested structures
- JSON-breaking characters
- Prompt injection resistance
- Error handling with unprintable characters

### `test_agent_retry_character_handling.py`
Retry mechanism and error handling tests including:
- Retry behavior with unicode inputs
- Encoding error handling
- Error message formatting
- History tracking with character data
- Cache behavior during retries

### `test_agent_config_character_handling.py`
Configuration and initialization tests including:
- Unicode in configuration values
- Special characters in environment variables
- Tool name validation
- Logging configuration with characters
- Edge cases in initialization

## Running the Tests

### Run All Character Tests
```bash
# From the project root
python -m pytest tests/character-test/ -v

# Or from the character-test directory
python -m pytest . -v
```

### Run Individual Test Files
```bash
python -m pytest tests/character-test/test_agent_character.py -v
python -m pytest tests/character-test/test_agent_parsing_edge_cases.py -v
python -m pytest tests/character-test/test_agent_retry_character_handling.py -v
python -m pytest tests/character-test/test_agent_config_character_handling.py -v
```

### Run Specific Test Classes
```bash
python -m pytest tests/character-test/test_agent_character.py::TestAgentCharacterHandling -v
python -m pytest tests/character-test/test_agent_parsing_edge_cases.py::TestAgentJSONParsingEdgeCases -v
```

### Run with Coverage
```bash
python -m pytest tests/character-test/ --cov=tinyagent.agent --cov-report=html
```

## Test Categories

### 1. Basic Character Handling
- **Empty/Null inputs**: Tests with empty strings, null values, whitespace
- **Single characters**: Minimal input validation
- **ASCII characters**: Standard ASCII character set
- **Extended ASCII**: Characters beyond basic ASCII range

### 2. Unicode and Internationalization
- **Unicode characters**: Various Unicode code points
- **Emoji handling**: Modern emoji characters and sequences
- **Mixed scripts**: Multiple writing systems in one input
- **Right-to-left text**: Arabic, Hebrew scripts
- **Complex characters**: Combining characters, ligatures

### 3. Special and Control Characters
- **Control characters**: Newlines, tabs, carriage returns
- **Escape sequences**: Backslashes, quotes
- **JSON-breaking characters**: Characters that break JSON parsing
- **Binary data**: Non-printable characters
- **Null bytes**: Zero-byte characters

### 4. Security-Related Character Tests
- **Injection attempts**: SQL injection, XSS, prompt injection
- **Path traversal**: Directory traversal sequences
- **Unicode normalization**: Potential security issues with Unicode
- **Encoding attacks**: Various encoding-based attacks

### 5. Performance and Memory Tests
- **Large inputs**: Very long strings
- **Repeated patterns**: Memory usage with repetitive data
- **Gradual scaling**: Increasing input sizes
- **Memory pressure**: High memory usage scenarios

### 6. Error Handling and Edge Cases
- **Malformed inputs**: Invalid or corrupted data
- **Encoding errors**: Character encoding issues
- **Timeout scenarios**: Operations that might hang
- **Resource exhaustion**: Memory/CPU intensive operations

## Expected Behaviors

### Successful Cases
The Agent should handle these gracefully:
- Valid Unicode text in all supported languages
- Standard special characters and escape sequences
- Reasonable input sizes (up to several MB)
- Common emoji and symbol characters
- Mixed character encodings

### Error Cases
The Agent should fail gracefully for:
- Extremely large inputs (>100MB)
- Invalid Unicode sequences
- Malicious injection attempts
- Corrupted binary data
- Resource exhaustion scenarios

### Retry Cases
The Agent should retry appropriately for:
- Temporary encoding issues
- Network-related character transmission problems
- Parsing failures due to character formatting
- Tool execution failures with character data

## Configuration Requirements

These tests require:
- `OPENROUTER_API_KEY` environment variable set
- Valid `config.yml` with `base_url` configured
- Python packages: `pytest`, `unicodedata` (built-in)
- Optional: `pytest-cov` for coverage reports

## Test Data Sources

Character test data includes:
- Unicode test strings from various languages
- Common emoji sequences
- Security test payloads (safely neutralized)
- Binary data representations
- Malformed input examples
- Performance stress test data

## Maintenance Notes

When adding new character tests:
1. Consider both positive and negative test cases
2. Include appropriate error handling expectations
3. Test with realistic input sizes
4. Document any platform-specific behaviors
5. Ensure tests are deterministic and reproducible

## Performance Considerations

Some tests may be slower due to:
- Large input processing
- Multiple retry attempts
- Unicode normalization operations
- Memory allocation/deallocation cycles

Consider using `pytest -x` to stop on first failure during development.

## Platform-Specific Notes

- **Windows**: May have different Unicode handling in file paths
- **macOS**: Unicode normalization may behave differently
- **Linux**: Generally most compatible with Unicode operations
- **Docker**: Character encoding may depend on container configuration

## Debugging Tips

For debugging character-related issues:
1. Use `repr()` to see exact character codes
2. Check `sys.getdefaultencoding()` for default encoding
3. Use `unicodedata.name()` to identify specific characters
4. Enable debug logging to see internal character processing
5. Test with minimal character sets first, then expand

## Contributing

When contributing character tests:
- Follow the existing test structure and naming conventions
- Include both edge cases and common use cases  
- Document any new character categories being tested
- Ensure tests are cross-platform compatible
- Add appropriate timeout values for long-running tests