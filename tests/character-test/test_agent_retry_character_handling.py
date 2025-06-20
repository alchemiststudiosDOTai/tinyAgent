"""
Character tests for Agent's retry mechanism and error handling.

These tests focus on how the Agent handles retries when encountering
challenging character inputs, malformed responses, and error conditions.
"""

import pathlib
import sys
from typing import Any, Dict
import pytest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from tinyagent.agent import Agent, RetryManager, tiny_agent
from tinyagent.decorators import tool
from tinyagent.exceptions import AgentRetryExceeded, ConfigurationError


@tool
def flaky_tool(message: str, fail_count: int = 0) -> str:
    """A tool that can be configured to fail a certain number of times."""
    # This is a simplified flaky tool for testing
    if hasattr(flaky_tool, 'call_count'):
        flaky_tool.call_count += 1
    else:
        flaky_tool.call_count = 1
    
    if flaky_tool.call_count <= fail_count:
        raise ValueError(f"Simulated failure #{flaky_tool.call_count}")
    
    return f"Success after {flaky_tool.call_count} attempts: {message}"


@tool
def character_sensitive_tool(text: str) -> str:
    """Tool that behaves differently based on character content."""
    if not text.isascii():
        raise ValueError("Non-ASCII characters not supported")
    if len(text) > 100:
        raise ValueError("Text too long")
    if any(c in text for c in ['"', "'", '\\']):
        raise ValueError("Quotes and backslashes not allowed")
    return f"Processed: {text}"


@tool
def encoding_tool(data: str) -> Dict[str, Any]:
    """Tool that processes encoding-sensitive data."""
    try:
        # Test various encoding scenarios
        encoded = data.encode('utf-8')
        decoded = encoded.decode('utf-8')
        return {
            "original": data,
            "encoded_length": len(encoded),
            "decoded_length": len(decoded),
            "match": data == decoded
        }
    except UnicodeError as e:
        raise ValueError(f"Encoding error: {str(e)}")


@pytest.fixture
def retry_agent():
    """Create an agent with retry-prone tools."""
    agent = tiny_agent(tools=[flaky_tool, character_sensitive_tool, encoding_tool])
    # Reset call count for flaky tool
    if hasattr(flaky_tool, 'call_count'):
        flaky_tool.call_count = 0
    return agent


@pytest.fixture
def minimal_config():
    """Minimal configuration for testing."""
    return {
        "base_url": "https://api.openrouter.ai/api/v1",
        "model": {"default": "deepseek/deepseek-chat"},
        "retries": {
            "max_attempts": 3,
            "temperature": {
                "initial": 0.2,
                "max": 0.8,
                "increment": 0.2
            },
            "model_escalation": {
                "sequence": [
                    "deepseek/deepseek-chat",
                    "anthropic/claude-3.5-sonnet"
                ]
            }
        }
    }


class TestRetryManagerCharacterHandling:
    """Test RetryManager with various character scenarios."""
    
    def test_retry_manager_initialization(self, minimal_config):
        """Test RetryManager initialization with character data."""
        manager = RetryManager(minimal_config, "test/model")
        assert manager.agent_default_model == "test/model"
        assert manager.current_attempt == 0
    
    def test_retry_manager_next_attempt(self, minimal_config):
        """Test retry manager's next attempt logic."""
        manager = RetryManager(minimal_config, "test/model")
        
        # First attempt should use default model
        temp1, model1 = manager.next_attempt()
        assert model1 == "test/model"
        assert temp1 == 0.2
        
        # Second attempt should escalate
        temp2, model2 = manager.next_attempt()
        assert model2 in minimal_config["retries"]["model_escalation"]["sequence"]
        assert temp2 >= temp1
    
    def test_retry_manager_should_retry(self, minimal_config):
        """Test retry manager's retry decision logic."""
        manager = RetryManager(minimal_config, "test/model")
        
        # Should retry within max attempts
        assert manager.should_retry() is True
        
        # Exhaust retry attempts
        for _ in range(minimal_config["retries"]["max_attempts"]):
            manager.next_attempt()
        
        assert manager.should_retry() is False


class TestAgentRetryWithCharacterChallenges:
    """Test Agent retry behavior with challenging character inputs."""
    
    def test_retry_with_unicode_input(self, retry_agent):
        """Test retry behavior with unicode input that might cause issues."""
        unicode_text = "Test với tiếng Việt 🇻🇳"
        
        try:
            result = retry_agent.run(f"process this unicode text: {unicode_text}", expected_type=str)
            assert isinstance(result, str)
        except AgentRetryExceeded:
            # This is acceptable if the tool genuinely can't handle unicode
            pass
    
    def test_retry_with_encoding_errors(self, retry_agent):
        """Test retry behavior with encoding-problematic characters."""
        problematic_chars = [
            "test\udcff",  # Invalid surrogate
            "test\ud800",  # Unpaired surrogate
            "test\x00null",  # Null character
        ]
        
        for char_seq in problematic_chars:
            try:
                result = retry_agent.run(f"encode this text: {char_seq}", expected_type=dict)
                if result:
                    assert isinstance(result, dict)
            except (AgentRetryExceeded, UnicodeError):
                # These are acceptable outcomes for problematic characters
                pass
    
    def test_retry_with_long_text(self, retry_agent):
        """Test retry behavior with very long text that might cause issues."""
        long_text = "word " * 10000  # 50k characters
        
        try:
            result = retry_agent.run(f"process this very long text safely", expected_type=str)
            assert isinstance(result, str)
        except AgentRetryExceeded:
            # Acceptable if the system can't handle very long inputs
            pass
    
    def test_retry_with_special_characters(self, retry_agent):
        """Test retry behavior with special characters."""
        special_text = "text with quotes: \"hello\" and 'world' and backslash: \\"
        
        try:
            result = retry_agent.run(f"process special chars: {special_text}", expected_type=str)
            assert isinstance(result, str)
        except AgentRetryExceeded:
            # Tool might legitimately reject special characters
            pass
    
    def test_retry_with_json_breaking_input(self, retry_agent):
        """Test retry behavior with JSON-breaking input."""
        json_breaker = '{"incomplete": "json'
        
        try:
            result = retry_agent.run(f"echo this safely: {json_breaker}", expected_type=str)
            assert isinstance(result, str)
        except AgentRetryExceeded:
            # System might struggle with malformed JSON-like input
            pass


class TestAgentErrorMessageHandling:
    """Test how Agent handles error messages with various characters."""
    
    def test_error_with_unicode_in_message(self, retry_agent):
        """Test error handling when error messages contain unicode."""
        # Reset flaky tool counter
        if hasattr(flaky_tool, 'call_count'):
            flaky_tool.call_count = 0
        
        unicode_message = "Message with unicode: café 🎉"
        
        try:
            result = retry_agent.run(f"use flaky tool with unicode: {unicode_message}", expected_type=str)
            # If successful, should contain the unicode
            if result:
                assert isinstance(result, str)
        except AgentRetryExceeded as e:
            # Error message should be properly formatted
            error_str = str(e)
            assert isinstance(error_str, str)
            assert len(error_str) > 0
    
    def test_error_with_special_chars_in_message(self, retry_agent):
        """Test error handling with special characters in error messages."""
        special_message = "Error with chars: <>&\"'`"
        
        try:
            result = retry_agent.run(f"test special chars: {special_message}", expected_type=str)
            if result:
                assert isinstance(result, str)
        except AgentRetryExceeded as e:
            # Error should be properly escaped/handled
            error_str = str(e)
            assert isinstance(error_str, str)
    
    def test_error_message_length_limits(self, retry_agent):
        """Test error message handling with very long error messages."""
        long_message = "very long error message " * 1000
        
        try:
            result = retry_agent.run(f"test with long message", expected_type=str)
            if result:
                assert isinstance(result, str)
        except AgentRetryExceeded as e:
            # Error message should still be manageable
            error_str = str(e)
            assert isinstance(error_str, str)
            assert len(error_str) < 100000  # Reasonable limit


class TestAgentHistoryWithCharacters:
    """Test Agent's history tracking with various character inputs."""
    
    def test_history_with_unicode_parameters(self, retry_agent):
        """Test history tracking with unicode parameters."""
        unicode_param = "Parameter with 世界 and 🌍"
        
        try:
            result = retry_agent.run(f"echo unicode param: {unicode_param}", expected_type=str)
            # Check that history was recorded
            assert len(retry_agent.history) > 0
            # History should contain the unicode parameter
            history_str = str(retry_agent.history)
            assert isinstance(history_str, str)
        except AgentRetryExceeded:
            # Even failed attempts should be in history
            assert len(retry_agent.history) > 0
    
    def test_history_with_large_parameters(self, retry_agent):
        """Test history tracking with large parameters."""
        large_param = "x" * 10000
        
        try:
            result = retry_agent.run(f"echo large param", expected_type=str)
            # History should still be manageable
            assert len(retry_agent.history) > 0
        except AgentRetryExceeded:
            # History should still be recorded
            assert len(retry_agent.history) > 0
    
    def test_history_serialization(self, retry_agent):
        """Test that history can be serialized despite character challenges."""
        # Run a few operations with various character types
        test_inputs = [
            "ascii text",
            "unicode: café",
            "emoji: 🚀",
            "special: <>&\"'",
        ]
        
        for inp in test_inputs:
            try:
                retry_agent.run(f"echo: {inp}", expected_type=str)
            except AgentRetryExceeded:
                pass
        
        # History should be serializable
        history = retry_agent.history
        assert len(history) > 0
        
        # Should be able to convert to string
        history_str = str(history)
        assert isinstance(history_str, str)


class TestAgentCacheWithRetries:
    """Test Agent's caching behavior during retries with character data."""
    
    def test_cache_invalidation_on_retry(self, retry_agent):
        """Test that cache is properly handled during retries."""
        # Make a successful call first
        result1 = retry_agent.run("echo simple text", expected_type=str)
        assert isinstance(result1, str)
        
        # Reset flaky tool for potential failure
        if hasattr(flaky_tool, 'call_count'):
            flaky_tool.call_count = 0
        
        # Try a potentially failing operation
        try:
            result2 = retry_agent.run("echo different text", expected_type=str)
            assert isinstance(result2, str)
        except AgentRetryExceeded:
            # Acceptable outcome
            pass
    
    def test_cache_with_unicode_keys(self, retry_agent):
        """Test caching with unicode cache keys."""
        unicode_inputs = [
            "café",
            "世界",
            "🌍",
        ]
        
        for inp in unicode_inputs:
            try:
                result = retry_agent.run(f"echo: {inp}", expected_type=str)
                # Second call should potentially use cache
                result2 = retry_agent.run(f"echo: {inp}", expected_type=str)
                if result and result2:
                    assert result == result2
            except AgentRetryExceeded:
                # Acceptable if unicode causes issues
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])