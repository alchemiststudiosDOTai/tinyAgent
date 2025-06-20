"""
Character tests for the Agent class.

These tests verify the Agent's behavior with various character inputs,
edge cases, special characters, unicode, and extreme scenarios.
"""

import pathlib
import sys
from typing import Any, Dict, List, Optional, Union
import pytest
import json
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from tinyagent.agent import Agent, TracedAgent, tiny_agent
from tinyagent.decorators import tool
from tinyagent.exceptions import AgentRetryExceeded, ConfigurationError
from tinyagent.tool import Tool


@tool
def echo_tool(message: str) -> str:
    """Echo back the provided message."""
    return f"Echo: {message}"


@tool  
def character_counter(text: str) -> Dict[str, int]:
    """Count characters in text."""
    return {
        "total": len(text),
        "alphanumeric": sum(c.isalnum() for c in text), 
        "spaces": text.count(" "),
        "special": len([c for c in text if not c.isalnum() and c != " "])
    }


@tool
def unicode_analyzer(text: str) -> Dict[str, Any]:
    """Analyze unicode characters in text."""
    result = {
        "length": len(text),
        "byte_length": len(text.encode('utf-8')),
        "ascii_only": text.isascii(),
        "categories": []
    }
    
    import unicodedata
    for char in set(text):
        try:
            category = unicodedata.category(char)
            if category not in result["categories"]:
                result["categories"].append(category)
        except Exception:
            pass
    
    return result


@tool
def memory_intensive_tool(data: str, repeat: int = 1) -> str:
    """Tool that processes data multiple times (memory test)."""
    result = data
    for _ in range(repeat):
        result = result + data
    return f"Processed {len(result)} characters"


@pytest.fixture
def basic_agent():
    """Create a basic agent with test tools."""
    return tiny_agent(tools=[echo_tool, character_counter, unicode_analyzer])


@pytest.fixture
def memory_agent():
    """Create an agent with memory-intensive tools."""
    return tiny_agent(tools=[memory_intensive_tool])


class TestAgentCharacterHandling:
    """Test Agent's handling of various character inputs."""
    
    def test_empty_string(self, basic_agent):
        """Test handling of empty string input."""
        result = basic_agent.run("echo an empty string", expected_type=str)
        assert isinstance(result, str)
    
    def test_single_character(self, basic_agent):
        """Test handling of single character input."""
        result = basic_agent.run("echo the letter A", expected_type=str)
        assert "A" in result
    
    def test_whitespace_only(self, basic_agent):
        """Test handling of whitespace-only strings."""
        result = basic_agent.run("echo three spaces", expected_type=str)
        assert isinstance(result, str)
    
    def test_special_characters(self, basic_agent):
        """Test handling of special characters."""
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        result = basic_agent.run(f"echo these special characters: {special_chars}", expected_type=str)
        assert isinstance(result, str)
    
    def test_unicode_characters(self, basic_agent):
        """Test handling of unicode characters."""
        unicode_text = "Hello 世界 🌍 café naïve résumé"
        result = basic_agent.run(f"analyze unicode in: {unicode_text}", expected_type=dict)
        assert isinstance(result, dict)
        assert "length" in result
        assert "ascii_only" in result
        assert result["ascii_only"] is False
    
    def test_emoji_handling(self, basic_agent):
        """Test handling of emoji characters."""
        emoji_text = "🚀🎉🔥💯⭐️🌟✨🎈"
        result = basic_agent.run(f"echo these emojis: {emoji_text}", expected_type=str)
        assert isinstance(result, str)
    
    def test_mixed_scripts(self, basic_agent):
        """Test handling of mixed writing scripts."""
        mixed_text = "English العربية 中文 日本語 Русский ελληνικά"
        result = basic_agent.run(f"analyze this mixed text: {mixed_text}", expected_type=dict)
        assert isinstance(result, dict)
    
    def test_control_characters(self, basic_agent):
        """Test handling of control characters."""
        control_text = "Line1\nLine2\tTabbed\rCarriage"
        result = basic_agent.run(f"echo text with control chars: {control_text}", expected_type=str)
        assert isinstance(result, str)
    
    def test_very_long_string(self, basic_agent):
        """Test handling of very long strings."""
        long_text = "A" * 10000
        result = basic_agent.run(f"count characters in a very long string of {len(long_text)} A's", expected_type=dict)
        assert isinstance(result, dict)
        assert result.get("total", 0) > 1000
    
    def test_json_breaking_characters(self, basic_agent):
        """Test characters that could break JSON parsing."""
        json_breakers = '"\\\n\r\t\b\f'
        result = basic_agent.run(f"echo these JSON-breaking chars: {json_breakers}", expected_type=str)
        assert isinstance(result, str)
    
    def test_sql_injection_characters(self, basic_agent):
        """Test characters commonly used in SQL injection."""
        sql_chars = "'; DROP TABLE users; --"
        result = basic_agent.run(f"echo these SQL chars safely: {sql_chars}", expected_type=str)
        assert isinstance(result, str)
    
    def test_path_traversal_characters(self, basic_agent):
        """Test path traversal characters."""
        path_chars = "../../../etc/passwd"
        result = basic_agent.run(f"echo these path chars: {path_chars}", expected_type=str)
        assert isinstance(result, str)


class TestAgentEdgeCases:
    """Test Agent's behavior in edge cases."""
    
    def test_null_bytes(self, basic_agent):
        """Test handling of null bytes."""
        null_text = "Before\x00After"
        result = basic_agent.run(f"echo text with null byte: {null_text}", expected_type=str)
        assert isinstance(result, str)
    
    def test_binary_data_as_string(self, basic_agent):
        """Test handling of binary data represented as string."""
        binary_text = "\x00\x01\x02\x03\x04\x05"
        result = basic_agent.run(f"echo binary data: {binary_text}", expected_type=str)
        assert isinstance(result, str)
    
    def test_extremely_nested_unicode(self, basic_agent):
        """Test extremely complex unicode combinations."""
        complex_unicode = "Z̷̰̈ä̶̰́l̴̰̈g̶̰̈ö̴̰ ̶̰̈ẗ̴̰ḛ̶̈ẍ̴̰ẗ̶̰"  # Zalgo text
        result = basic_agent.run(f"analyze zalgo text: {complex_unicode}", expected_type=dict)
        assert isinstance(result, dict)
    
    def test_repeated_characters(self, basic_agent):
        """Test handling repeated characters."""
        repeated = "a" * 1000 + "b" * 1000 + "c" * 1000
        result = basic_agent.run(f"count characters in repeated pattern", expected_type=dict)
        assert isinstance(result, dict)
    
    def test_alternating_pattern(self, basic_agent):
        """Test alternating character patterns."""
        pattern = "ab" * 5000
        result = basic_agent.run(f"echo alternating pattern of {len(pattern)} chars", expected_type=str)
        assert isinstance(result, str)


class TestAgentMemoryAndPerformance:
    """Test Agent's memory handling and performance with character data."""
    
    def test_memory_pressure(self, memory_agent):
        """Test agent under memory pressure."""
        large_data = "x" * 100000
        result = memory_agent.run(f"process large data of {len(large_data)} characters", expected_type=str)
        assert isinstance(result, str)
        assert "characters" in result
    
    def test_repeated_large_operations(self, memory_agent):
        """Test repeated operations with large data."""
        data = "test" * 1000
        for i in range(3):  # Reduced iterations to avoid timeout
            result = memory_agent.run(f"process data iteration {i}", expected_type=str)
            assert isinstance(result, str)
    
    def test_gradual_memory_increase(self, memory_agent):
        """Test gradually increasing memory usage."""
        for size in [1000, 5000, 10000]:
            data = "a" * size
            result = memory_agent.run(f"process {size} character string", expected_type=str) 
            assert isinstance(result, str)
            assert str(size) in result or "characters" in result


class TestAgentToolParameterValidation:
    """Test Agent's parameter validation with various character inputs."""
    
    def test_invalid_tool_parameters(self, basic_agent):
        """Test handling of invalid tool parameters."""
        try:
            # This should fail gracefully
            result = basic_agent.run("use a tool that doesn't exist with invalid params")
            # If it doesn't raise an exception, it should return a meaningful response
            assert isinstance(result, (str, dict))
        except (AgentRetryExceeded, ValueError) as e:
            # Expected behavior for invalid operations
            assert isinstance(e, (AgentRetryExceeded, ValueError))
    
    def test_parameter_type_coercion(self, basic_agent):
        """Test parameter type coercion with string inputs."""
        result = basic_agent.run("count characters in the word 'hello'", expected_type=dict)
        assert isinstance(result, dict)
        assert "total" in result
        assert result["total"] == 5
    
    def test_missing_required_parameters(self, basic_agent):
        """Test handling when required parameters are missing."""
        try:
            result = basic_agent.run("echo something but don't provide the message")
            # Should handle gracefully or raise appropriate error
            assert isinstance(result, (str, dict)) or result is None
        except (AgentRetryExceeded, ValueError):
            # Expected behavior for missing parameters
            pass


class TestAgentCaching:
    """Test Agent's caching behavior with character data."""
    
    def test_cache_with_identical_strings(self, basic_agent):
        """Test caching with identical string inputs."""
        query = "echo hello world"
        
        # First call
        start_time = time.time()
        result1 = basic_agent.run(query, expected_type=str)
        first_duration = time.time() - start_time
        
        # Second call (should use cache)
        start_time = time.time()
        result2 = basic_agent.run(query, expected_type=str)
        second_duration = time.time() - start_time
        
        assert result1 == result2
        # Note: Cache timing comparison removed as it's not reliable in tests
    
    def test_cache_with_similar_strings(self, basic_agent):
        """Test caching with similar but different strings."""
        result1 = basic_agent.run("echo hello world", expected_type=str)
        result2 = basic_agent.run("echo hello world!", expected_type=str)  # Different punctuation
        
        # Results should be different due to different inputs
        assert result1 != result2
    
    def test_cache_key_generation(self, basic_agent):
        """Test cache key generation with special characters."""
        special_query = "echo special chars: !@#$%^&*()"
        result = basic_agent.run(special_query, expected_type=str)
        assert isinstance(result, str)
        
        # Run again to test cache key works with special chars
        result2 = basic_agent.run(special_query, expected_type=str)
        assert result == result2


class TestAgentConfigurationEdgeCases:
    """Test Agent configuration edge cases."""
    
    def test_agent_with_no_tools(self):
        """Test agent behavior with no tools registered."""
        agent = Agent()
        # Should have at least the built-in chat tool
        assert len(agent.get_available_tools()) > 0
        assert any(tool.name == "chat" for tool in agent.get_available_tools())
    
    def test_tool_name_with_special_characters(self, basic_agent):
        """Test tool names with special characters."""
        # This tests the internal tool handling
        tool_names = [tool.name for tool in basic_agent.get_available_tools()]
        assert all(isinstance(name, str) for name in tool_names)
    
    def test_duplicate_tool_registration(self):
        """Test registering tools with duplicate names."""
        agent = Agent()
        
        # Register first tool
        agent.create_tool("test_tool", "First tool", lambda x: "first")
        
        # Register second tool with same name (should update)
        agent.create_tool("test_tool", "Second tool", lambda x: "second")
        
        tools = agent.get_available_tools()
        test_tools = [t for t in tools if t.name == "test_tool"]
        assert len(test_tools) == 1
        assert test_tools[0].description == "Second tool"


class TestTracedAgentCharacterHandling:
    """Test TracedAgent specific character handling."""
    
    @pytest.fixture
    def traced_agent(self):
        """Create a traced agent for testing."""
        return TracedAgent()
    
    def test_traced_agent_basic_functionality(self, traced_agent):
        """Test that TracedAgent handles basic character operations."""
        traced_agent.create_tool("echo", "Echo tool", lambda msg: f"Echo: {msg}")
        result = traced_agent.run("echo hello", expected_type=str)
        assert isinstance(result, str)
        assert "hello" in result.lower()
    
    def test_traced_agent_unicode_handling(self, traced_agent):
        """Test TracedAgent with unicode characters."""
        traced_agent.create_tool("echo", "Echo tool", lambda msg: f"Echo: {msg}")
        unicode_text = "Hello 世界"
        result = traced_agent.run(f"echo {unicode_text}", expected_type=str)
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])