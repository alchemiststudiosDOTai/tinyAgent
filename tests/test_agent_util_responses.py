"""
Test suite for the simple calculator tool functionality.
Tests the basic tool registration and agent execution with a simple calculator tool.
"""

import sys
import os
import pytest
from typing import Callable
from unittest.mock import patch, MagicMock

# Setup path for local package imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Local package imports
from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent
from tinyagent.tool import Tool
from tinyagent.exceptions import AgentRetryExceeded

@pytest.fixture
def calculator_tool() -> Callable[[int, int], int]:
    """Fixture providing a simple calculator tool for testing."""
    @tool
    def calculate_sum(a: int, b: int) -> int:
        """Calculate the sum of two integers."""
        return a + b
    
    return calculate_sum

@pytest.fixture
def agent_with_calculator(calculator_tool) -> tiny_agent:
    """Fixture providing an agent initialized with the calculator tool."""
    return tiny_agent(tools=[calculator_tool])

def test_tool_registration(calculator_tool):
    """Test that the tool is properly registered with the @tool decorator."""
    # Verify tool has required attributes
    assert hasattr(calculator_tool, '_tool'), "Tool not properly registered"
    assert isinstance(calculator_tool._tool, Tool), "Tool attribute is not a Tool instance"
    assert calculator_tool.__doc__ is not None, "Tool missing docstring"
    assert calculator_tool.__annotations__.get('return') == int, "Tool missing return type annotation"
    assert all(param in calculator_tool.__annotations__ for param in ['a', 'b']), "Tool missing parameter type annotations"

def test_direct_tool_execution(calculator_tool):
    """Test that the tool can be called directly with correct results."""
    assert calculator_tool(5, 3) == 8, "Direct tool execution failed"
    assert calculator_tool(-1, 1) == 0, "Tool fails with negative numbers"
    assert calculator_tool(0, 0) == 0, "Tool fails with zero"
    assert calculator_tool(999999, 1) == 1000000, "Tool fails with large numbers"

@pytest.mark.parametrize("query,expected", [
    ("calculate the sum of 7 and 4", 11),
    ("add 0 and 0", 0),
    ("what is -1 plus 5", 4),
    ("sum up 100 and 200", 300),
])
def test_agent_execution(agent_with_calculator, query: str, expected: int):
    """Test that the agent correctly interprets queries and executes the tool."""
    # Mock the OpenRouter API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "calculate_sum", "arguments": {"a": ' + str(expected - 4) + ', "b": 4}}'
            }
        }]
    }
    
    with patch('requests.post', return_value=mock_response):
        result = agent_with_calculator.run(query, expected_type=int)
        assert isinstance(result, int), "Agent did not return an integer"
        assert result == expected, f"Agent returned incorrect result for query: {query}"

def test_agent_chat_fallback(agent_with_calculator):
    """Test that the agent uses chat as a last-ditch attempt when explicitly requested."""
    # Mock the OpenRouter API response with a chat fallback
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "chat", "arguments": {"message": "I apologize, but I cannot find a suitable tool to handle weather information. Since you asked to chat, I can tell you that I don\'t have access to current weather data."}}'
            }
        }]
    }
    
    # Test that when user explicitly mentions "chat", agent allows the chat fallback
    with patch('requests.post', return_value=mock_response):
        result = agent_with_calculator.run("chat with me about the weather today")
        
        # Verify we got a proper chat response
        assert isinstance(result, str), "Chat fallback should return a string"
        assert "weather" in result.lower(), "Chat response should acknowledge the original query"
        assert "don't have access" in result.lower(), "Chat should explain its limitations"

def test_chat_fallback_rejection(agent_with_calculator):
    """Test that the agent rejects unwanted chat fallbacks for security."""
    # Mock the OpenRouter API response with a chat fallback
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "chat", "arguments": {"message": "I apologize, but I cannot find a suitable tool to handle weather information. As a fallback, I am responding via chat."}}'
            }
        }]
    }
    
    # Test that when LLM tries to fall back to chat inappropriately, agent rejects it and raises exception
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(AgentRetryExceeded) as exc_info:
            agent_with_calculator.run("what is the weather today?")
        
        # Verify the error message indicates the issue
        error_message = str(exc_info.value)
        assert "Failed to get valid response" in error_message, "Exception should indicate retry failure"
        
        # Verify retry history contains the specific error about no valid tool found
        history = exc_info.value.history if hasattr(exc_info.value, 'history') else []
        error_found = any("No valid tool found for query" in str(entry.get('error', '')) for entry in history)
        assert error_found, "Retry history should indicate 'No valid tool found for query'"

def test_agent_error_handling(agent_with_calculator):
    """Test that the agent handles invalid tool arguments appropriately."""
    # Mock the OpenRouter API response for non-numeric values
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "calculate_sum", "arguments": {"a": "apple", "b": "banana"}}'
            }
        }]
    }
    
    # Test query with non-numeric values should raise error
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(AgentRetryExceeded) as exc_info:
            agent_with_calculator.run("add apple and banana", expected_type=int)
        
        # Verify the error message indicates retry failure
        error_message = str(exc_info.value)
        assert "Failed to get valid response" in error_message, "Exception should indicate retry failure"
        
        # Verify retry history contains validation errors about invalid arguments
        history = exc_info.value.history if hasattr(exc_info.value, 'history') else []
        error_found = any("Parameter a must be an integer" in str(entry.get('error', '')) for entry in history)
        assert error_found, "Retry history should indicate parameter type validation error"

def test_agent_type_validation(agent_with_calculator):
    """Test that the agent properly validates return types."""
    # Mock the OpenRouter API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "calculate_sum", "arguments": {"a": 1, "b": 2}}'
            }
        }]
    }
    
    # Test requesting wrong return type (set is not directly supported by the converter)
    with patch('requests.post', return_value=mock_response):
        with pytest.raises(AgentRetryExceeded) as exc_info:
            agent_with_calculator.run("add 1 and 2", expected_type=set)
        
        # Verify the error message indicates retry failure
        error_message = str(exc_info.value)
        assert "Failed to get valid response" in error_message, "Exception should indicate retry failure"
        
        # Verify retry history contains validation errors about type conversion
        history = exc_info.value.history if hasattr(exc_info.value, 'history') else []
        error_found = any("Unsupported expected_type" in str(entry.get('error', '')) for entry in history)
        assert error_found, "Retry history should indicate type conversion error with unsupported type"

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

def test_agent_edge_cases(agent_with_calculator):
    """Test edge cases and boundary conditions."""
    # Mock the OpenRouter API response for large numbers
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "calculate_sum", "arguments": {"a": 999999999, "b": 1}}'
            }
        }]
    }
    
    # Test large numbers
    with patch('requests.post', return_value=mock_response):
        result = agent_with_calculator.run("add 999999999 and 1", expected_type=int)
        assert result == 1000000000, "Agent failed with large numbers"
    
    # Mock the OpenRouter API response for negative numbers
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "calculate_sum", "arguments": {"a": -100, "b": -50}}'
            }
        }]
    }
    
    # Test negative numbers
    with patch('requests.post', return_value=mock_response):
        result = agent_with_calculator.run("add -100 and -50", expected_type=int)
        assert result == -150, "Agent failed with negative numbers"
    
    # Mock the OpenRouter API response for zero values
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"tool": "calculate_sum", "arguments": {"a": 0, "b": 0}}'
            }
        }]
    }
    
    # Test zero handling
    with patch('requests.post', return_value=mock_response):
        result = agent_with_calculator.run("add 0 and 0", expected_type=int)
        assert result == 0, "Agent failed with zero values"
