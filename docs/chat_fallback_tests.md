# Chat Fallback and Type Validation Tests

## Overview

This document outlines the implementation of tests for two critical behaviors in the tinyAgent framework:

1. **Chat Fallback Mechanism**: A dual-purpose feature that provides graceful degradation while maintaining security
2. **Type Validation & Conversion**: Error handling for return type expectations and conversions

## Chat Fallback Behavior

The chat fallback mechanism has a dual implementation:

### 1. Explicit Chat Requests (Security-First Design)

- When a query explicitly contains the word "chat", the agent permits using the chat tool as a fallback
- This is tested in `test_agent_chat_fallback`
- This behavior ensures that chat functionality is only used when explicitly requested

```python
def test_agent_chat_fallback(agent_with_calculator):
    """Test that the agent uses chat as a last-ditch attempt when explicitly requested."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "chat", "arguments": {"message": "..."}}'
            }
        }]
    }

    # Test that when user explicitly mentions "chat", agent allows the chat fallback
    with patch('requests.post', return_value=mock_response):
        result = agent_with_calculator.run("chat with me about the weather today")

        assert isinstance(result, str), "Chat fallback should return a string"
        assert "weather" in result.lower(), "Chat response should acknowledge the original query"
```

### 2. Rejection of Unwanted Fallbacks

- When a query does not contain "chat" but the model attempts to use the chat tool, the agent rejects this for security
- This is tested in `test_chat_fallback_rejection`
- This protection prevents unauthorized chat usage when users request tools

```python
def test_chat_fallback_rejection(agent_with_calculator):
    """Test that the agent rejects unwanted chat fallbacks for security."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "chat", "arguments": {"message": "..."}}'
            }
        }]
    }

    # Test rejection of unwanted chat fallbacks
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(AgentRetryExceeded) as exc_info:
            agent_with_calculator.run("what is the weather today?")

        # Verify error history contains specific security message
        history = exc_info.value.history if hasattr(exc_info.value, 'history') else []
        error_found = any("No valid tool found for query" in str(entry.get('error', '')) for entry in history)
        assert error_found, "Retry history should indicate security rejection"
```

## Type Validation Tests

Type validation tests verify that the agent correctly handles expected return types:

### 1. Error Handling for Unsupported Types

- When requesting conversion to unsupported types, the agent should error appropriately
- Due to the retry mechanism, errors are wrapped in `AgentRetryExceeded`
- Tests check retry history for original validation errors

```python
def test_agent_type_validation(agent_with_calculator):
    """Test that the agent properly validates return types."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "calculate_sum", "arguments": {"a": 1, "b": 2}}'
            }
        }]
    }

    # Test requesting wrong return type (set is not directly supported)
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(AgentRetryExceeded) as exc_info:
            agent_with_calculator.run("add 1 and 2", expected_type=set)

        # Verify retry history contains type conversion errors
        history = exc_info.value.history
        error_found = any("Unsupported expected_type" in str(entry.get('error', '')) for entry in history)
        assert error_found, "Should indicate type conversion error"
```

### 2. Supported Type Conversions

- Testing that supported conversions work correctly:
  - Integer to Float
  - Integer to String

```python
# Test correct return type - int can be converted to float
with patch('requests.post', return_value=mock_response):
    result = agent_with_calculator.run("add 1 and 2", expected_type=float)
    assert isinstance(result, float), "Agent failed to return correct type"
    assert result == 3.0, "Agent returned incorrect result"

# Test correct return type - int can be converted to string
with patch('requests.post', return_value=mock_response):
    result = agent_with_calculator.run("add 1 and 2", expected_type=str)
    assert isinstance(result, str), "Agent failed to return correct type"
    assert result == "3", "Agent returned incorrect result"
```

## Key Lessons

1. **Error Propagation**: Due to the retry mechanism, original exceptions are wrapped in `AgentRetryExceeded`. Tests must check retry history for original errors.

2. **Security First**: Chat fallback is a dual-purpose feature:

   - Helpful when explicitly requested
   - Protective against unwanted usage

3. **Type System**: The type conversion system supports a limited set of types (str, int, float, bool, list, dict) and rejects others.

These tests ensure that both features work as intended while maintaining the security model of the agent framework.
