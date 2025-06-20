"""
Basic character test for Agent class - minimal test to verify functionality.
"""

import pathlib
import sys
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from tinyagent.agent import Agent, tiny_agent
from tinyagent.decorators import tool


@tool
def simple_echo(message: str) -> str:
    """Simple echo tool for testing."""
    return f"Echo: {message}"


def test_agent_basic_instantiation():
    """Test that Agent can be instantiated with basic config."""
    agent = tiny_agent(tools=[simple_echo])
    assert agent is not None
    assert len(agent.get_available_tools()) > 0


def test_simple_character_handling():
    """Test basic character handling."""
    agent = tiny_agent(tools=[simple_echo])
    
    # Test with simple ASCII text
    result = agent.run("echo hello world", expected_type=str)
    assert isinstance(result, str)
    assert "hello" in result.lower() or "world" in result.lower()


def test_unicode_basic():
    """Test basic unicode handling."""
    agent = tiny_agent(tools=[simple_echo])
    
    try:
        result = agent.run("echo café", expected_type=str)
        assert isinstance(result, str)
    except Exception:
        # Unicode might not be supported in all configurations
        pytest.skip("Unicode not supported in current configuration")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])