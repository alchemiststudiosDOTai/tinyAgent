"""Tests for the tool decorator and basic functionality."""

import unittest
from typing import Dict, Any

# Add parent directory to path so we can import from the root level
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "...")))

from core.decorators import tool
from core.tool import Tool, ParamType


class TestToolDecorator(unittest.TestCase):
    """Test the tool decorator functionality."""

    def test_basic_tool_creation(self):
        """Test that a simple function can be converted to a tool."""
        
        @tool
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers together."""
            return a + b
        
        # Verify the function was converted to a Tool
        self.assertIsInstance(add_numbers, Tool)
        self.assertEqual(add_numbers.name, "add_numbers")
        self.assertEqual(add_numbers.parameters["a"], ParamType.INTEGER)
        self.assertEqual(add_numbers.parameters["b"], ParamType.INTEGER)
        
        # Verify the tool can be executed
        result = add_numbers.execute(a=5, b=3)
        self.assertEqual(result, 8)
    
    def test_tool_with_custom_name(self):
        """Test that a tool can be created with a custom name."""
        
        @tool(name="custom_adder")
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers together."""
            return a + b
        
        self.assertEqual(add_numbers.name, "custom_adder")
        
    def test_tool_with_description(self):
        """Test that a tool description is properly set."""
        
        description = "A tool that adds two numbers together"
        
        @tool(description=description)
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b
        
        self.assertEqual(add_numbers.description, description)


if __name__ == "__main__":
    unittest.main()
