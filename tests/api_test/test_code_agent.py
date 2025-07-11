"""
Tests for tinyagent.code_agent
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import load_dotenv

from tinyagent import tool
from tinyagent.agent import StepLimitReached
from tinyagent.code_agent import PythonExecutor, TinyCodeAgent
from tinyagent.tools import Tool

# Load .env file from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")


class TestPythonExecutor:
    """Test suite for PythonExecutor sandbox."""

    def test_basic_execution(self):
        """Test basic code execution."""
        executor = PythonExecutor()
        result, is_final = executor.run("x = 2 + 3\nprint(x)")
        assert result == "5"
        assert not is_final

    def test_final_answer(self):
        """Test final_answer sentinel."""
        executor = PythonExecutor()
        result, is_final = executor.run("final_answer(42)")
        assert result == "42"
        assert is_final

    def test_safe_builtins_allowed(self):
        """Test that safe builtins work."""
        executor = PythonExecutor()
        code = """
nums = [1, 2, 3, 4, 5]
print(f"sum: {sum(nums)}")
print(f"max: {max(nums)}")
print(f"len: {len(nums)}")
"""
        result, _ = executor.run(code)
        assert "sum: 15" in result
        assert "max: 5" in result
        assert "len: 5" in result

    def test_unsafe_builtins_blocked(self):
        """Test that unsafe builtins are blocked."""
        executor = PythonExecutor()

        # Test file operations blocked
        with pytest.raises(NameError):
            executor.run("open('test.txt', 'w')")

        # Test eval blocked
        with pytest.raises(NameError):
            executor.run("eval('1 + 1')")

        # Test exec blocked
        with pytest.raises(NameError):
            executor.run("exec('x = 1')")

    def test_import_whitelist(self):
        """Test import whitelist enforcement."""
        # Math allowed
        executor = PythonExecutor(extra_imports={"math"})
        result, _ = executor.run("import math\nprint(math.pi)")
        assert "3.14" in result

        # Random not allowed
        with pytest.raises(RuntimeError, match="Import 'random' not allowed"):
            executor.run("import random")

        # Submodules checked
        with pytest.raises(RuntimeError, match="Import 'os.path' not allowed"):
            executor.run("import os.path")

    def test_import_from_whitelist(self):
        """Test from imports whitelist."""
        executor = PythonExecutor(extra_imports={"math"})

        # Allowed
        result, _ = executor.run("from math import sqrt\nprint(sqrt(16))")
        assert "4.0" in result

        # Not allowed
        with pytest.raises(RuntimeError, match="Import from 'os' not allowed"):
            executor.run("from os import environ")

    def test_stdout_capture(self):
        """Test stdout is properly captured."""
        executor = PythonExecutor()
        code = """
print("Line 1")
print("Line 2")
x = 10
print(f"x = {x}")
"""
        result, _ = executor.run(code)
        assert result == "Line 1\nLine 2\nx = 10"

    def test_namespace_isolation(self):
        """Test that executions don't pollute namespace."""
        executor = PythonExecutor()

        # First execution
        executor.run("x = 100")

        # Second execution shouldn't see x
        with pytest.raises(NameError):
            executor.run("print(x)")

    def test_complex_calculation(self):
        """Test more complex calculations."""
        executor = PythonExecutor(extra_imports={"math"})
        code = """
import math

# Calculate area of circle
radius = 5
area = math.pi * radius ** 2

# Calculate circumference
circumference = 2 * math.pi * radius

print(f"Radius: {radius}")
print(f"Area: {area:.2f}")
print(f"Circumference: {circumference:.2f}")

final_answer({
    "radius": radius,
    "area": round(area, 2),
    "circumference": round(circumference, 2)
})
"""
        result, is_final = executor.run(code)
        assert is_final
        assert "78.54" in result  # area
        assert "31.42" in result  # circumference


class TestTinyCodeAgent:
    """Test suite for TinyCodeAgent."""

    def setup_method(self):
        """Setup test fixtures."""
        # Clear any existing tools from registry
        from tinyagent.tools import _REGISTRY

        _REGISTRY._data.clear()
        _REGISTRY._frozen = False

        # Create test tools
        @tool
        def add(a: float, b: float) -> float:
            """Add two numbers."""
            return a + b

        @tool
        def multiply(a: float, b: float) -> float:
            """Multiply two numbers."""
            return a * b

        @tool
        def get_data() -> dict:
            """Get some test data."""
            return {"users": 100, "revenue": 5000.50}

        self.add = add
        self.multiply = multiply
        self.get_data = get_data

        # Create Tool objects
        self.tools = [
            Tool(fn=add, name="add", doc="Add two numbers", signature=None),
            Tool(fn=multiply, name="multiply", doc="Multiply two numbers", signature=None),
            Tool(fn=get_data, name="get_data", doc="Get some test data", signature=None),
        ]

    def teardown_method(self):
        """Clean up after tests."""
        from tinyagent.tools import _REGISTRY

        _REGISTRY._data.clear()
        _REGISTRY._frozen = False

    def test_agent_initialization(self):
        """Test agent initialization."""
        agent = TinyCodeAgent(tools=self.tools, extra_imports=["math"])
        assert len(agent._tool_map) == 3
        assert "add" in agent._tool_map
        assert "multiply" in agent._tool_map

    def test_no_tools_raises_error(self):
        """Test that no tools raises ValueError."""
        with pytest.raises(ValueError, match="requires at least one tool"):
            TinyCodeAgent(tools=[])

    def test_simple_calculation(self):
        """Test simple calculation without tools."""
        agent = TinyCodeAgent(tools=self.tools)

        with patch.object(agent, "_chat") as mock_chat:
            mock_chat.return_value = """```python
# Simple calculation
result = 2 + 3
final_answer(result)
```"""

            result = agent.run("What is 2 + 3?")
            assert result == "5"

    def test_tool_usage(self):
        """Test using tools in Python code."""
        agent = TinyCodeAgent(tools=self.tools)

        with patch.object(agent, "_chat") as mock_chat:
            mock_chat.return_value = """```python
# Use add tool
sum_result = add(10, 20)
# Use multiply tool
product = multiply(sum_result, 2)
final_answer(product)
```"""

            result = agent.run("Add 10 and 20, then multiply by 2")
            assert result == "60"

    def test_multi_step_reasoning(self):
        """Test multi-step ReAct loop."""
        agent = TinyCodeAgent(tools=self.tools)

        with patch.object(agent, "_chat") as mock_chat:
            # First step: get data
            mock_chat.side_effect = [
                """```python
# First, get the data
data = get_data()
print(f"Users: {data['users']}")
print(f"Revenue: {data['revenue']}")
```""",
                """```python
# Calculate revenue per user
users = 100
revenue = 5000.50
revenue_per_user = revenue / users
final_answer(f"Revenue per user: ${revenue_per_user:.2f}")
```""",
            ]

            result = agent.run("What is the revenue per user?")
            assert "50.01" in result or "50.00" in result

    def test_code_extraction(self):
        """Test code block extraction."""
        # With python tag
        text = "Here's the code:\n```python\nprint('hello')\n```"
        code = TinyCodeAgent._extract_code(text)
        assert code == "print('hello')"

        # Without python tag
        text = "```\nx = 42\n```"
        code = TinyCodeAgent._extract_code(text)
        assert code == "x = 42"

        # No code block
        text = "Just some text"
        code = TinyCodeAgent._extract_code(text)
        assert code is None

    def test_execution_error_handling(self):
        """Test handling of execution errors."""
        agent = TinyCodeAgent(tools=self.tools)

        with patch.object(agent, "_chat") as mock_chat:
            mock_chat.side_effect = [
                """```python
# This will cause an error
result = 1 / 0
```""",
                """```python
# Fix the error
result = "Cannot divide by zero"
final_answer(result)
```""",
            ]

            result = agent.run("Divide 1 by 0")
            assert "Cannot divide by zero" in result

    def test_import_usage(self):
        """Test using allowed imports."""
        agent = TinyCodeAgent(tools=self.tools, extra_imports=["math", "json"])

        with patch.object(agent, "_chat") as mock_chat:
            mock_chat.return_value = """```python
import math
import json

# Calculate square root
num = 16
sqrt_result = math.sqrt(num)

# Create JSON result
result = json.dumps({
    "number": num,
    "square_root": sqrt_result
})

final_answer(result)
```"""

            result = agent.run("What is the square root of 16?")
            assert "4.0" in result
            assert "16" in result

    def test_step_limit(self):
        """Test step limit is enforced."""
        agent = TinyCodeAgent(tools=self.tools)

        with patch.object(agent, "_chat") as mock_chat:
            # Never provide final answer
            mock_chat.return_value = """```python
print("Still thinking...")
```"""

            with pytest.raises(StepLimitReached):
                agent.run("Solve this", max_steps=3)

            # Should have made 3 attempts
            assert mock_chat.call_count == 3

    def test_invalid_code_format(self):
        """Test handling of invalid code format."""
        agent = TinyCodeAgent(tools=self.tools)

        with patch.object(agent, "_chat") as mock_chat:
            mock_chat.side_effect = [
                "I'll calculate that for you",  # No code block
                """```python
final_answer(42)
```""",
            ]

            result = agent.run("What is the answer?")
            assert result == "42"

    def test_output_truncation(self):
        """Test that long outputs are truncated."""
        agent = TinyCodeAgent(tools=self.tools)

        with patch.object(agent, "_chat") as mock_chat:
            mock_chat.return_value = """```python
# Generate long output
long_text = "x" * 3000
final_answer(long_text)
```"""

            result = agent.run("Generate long text")
            assert len(result) == 2000  # MAX_OUTPUT_LENGTH

    def test_tool_in_loop(self):
        """Test using tools in a loop."""
        agent = TinyCodeAgent(tools=self.tools)

        with patch.object(agent, "_chat") as mock_chat:
            mock_chat.return_value = """```python
# Sum numbers using tool
numbers = [1, 2, 3, 4, 5]
total = 0
for i in range(len(numbers) - 1):
    total = add(total, numbers[i])
total = add(total, numbers[-1])
final_answer(total)
```"""

            result = agent.run("Sum the list [1,2,3,4,5] using the add tool")
            assert result == "15"
