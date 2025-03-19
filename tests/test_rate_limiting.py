"""Tests for the rate limiting functionality of tools."""

import unittest
import time
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "...")))

from core.decorators import tool
from core.exceptions import RateLimitExceeded
from core.factory import AgentFactory


class TestRateLimiting(unittest.TestCase):
    """Test the rate limiting functionality for tools."""

    def setUp(self):
        """Set up the test environment."""
        # Create a test configuration with rate limits
        self.config = {
            "rate_limits": {
                "global": 2,  # Default global limit
                "tools": {
                    "test_tool": 1,  # Specific limit for test_tool
                    "unlimited_tool": -1  # No limit
                }
            }
        }
        
        # Create a factory with our test config
        self.factory = AgentFactory.get_instance(self.config)
        
        # Reset the call counters for our test
        if hasattr(self.factory, "_call_counters"):
            self.factory._call_counters = {}
            self.factory._last_reset_time = time.time()
    
    def test_global_rate_limit(self):
        """Test that the global rate limit is enforced."""
        
        # Create a tool that uses the global rate limit
        @tool
        def global_limited_tool(value: str) -> str:
            """A tool with the global rate limit."""
            return f"Processed: {value}"
        
        # Register the tool
        self.factory.register_tool(global_limited_tool)
        
        # First two calls should succeed (global limit is 2)
        self.factory.execute_tool("global_limited_tool", value="test1")
        self.factory.execute_tool("global_limited_tool", value="test2")
        
        # Third call should fail due to rate limit
        with self.assertRaises(RateLimitExceeded):
            self.factory.execute_tool("global_limited_tool", value="test3")
    
    def test_tool_specific_rate_limit(self):
        """Test that tool-specific rate limits are enforced."""
        
        # Create a tool with a specific rate limit
        @tool(name="test_tool")
        def limited_tool(value: str) -> str:
            """A tool with a specific rate limit of 1."""
            return f"Processed: {value}"
        
        # Register the tool
        self.factory.register_tool(limited_tool)
        
        # First call should succeed
        self.factory.execute_tool("test_tool", value="test1")
        
        # Second call should fail due to tool-specific rate limit
        with self.assertRaises(RateLimitExceeded):
            self.factory.execute_tool("test_tool", value="test2")
    
    def test_unlimited_tool(self):
        """Test that tools with -1 rate limit have no limit."""
        
        # Create a tool with no rate limit
        @tool(name="unlimited_tool")
        def unlimited_tool(value: str) -> str:
            """A tool with no rate limit (-1)."""
            return f"Processed: {value}"
        
        # Register the tool
        self.factory.register_tool(unlimited_tool)
        
        # Multiple calls should succeed
        for i in range(10):  # Try 10 calls
            result = self.factory.execute_tool("unlimited_tool", value=f"test{i}")
            self.assertEqual(result, f"Processed: test{i}")


if __name__ == "__main__":
    unittest.main()
