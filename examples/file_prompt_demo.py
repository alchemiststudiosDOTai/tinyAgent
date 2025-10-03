#!/usr/bin/env python3
"""File-based prompt loading demo for tinyAgent."""

import ast
import operator
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Final

from tinyagent import ReactAgent, tool
from tinyagent.agents.code_agent import TinyCodeAgent

_BINARY_OPERATORS: Final[dict[type[ast.operator], Callable[[float, float], float]]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

_UNARY_OPERATORS: Final[dict[type[ast.unaryop], Callable[[float], float]]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_arithmetic(expression: str) -> float:
    """Evaluate a basic arithmetic expression using a restricted AST interpreter."""

    def _evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _evaluate(node.body)

        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)

        if isinstance(node, ast.BinOp):
            binary_operator_type = type(node.op)
            if binary_operator_type not in _BINARY_OPERATORS:
                msg = f"Unsupported operator: {binary_operator_type.__name__}"
                raise ValueError(msg)
            left = _evaluate(node.left)
            right = _evaluate(node.right)
            return _BINARY_OPERATORS[binary_operator_type](left, right)

        if isinstance(node, ast.UnaryOp):
            unary_operator_type = type(node.op)
            if unary_operator_type not in _UNARY_OPERATORS:
                msg = f"Unsupported unary operator: {unary_operator_type.__name__}"
                raise ValueError(msg)
            operand = _evaluate(node.operand)
            return _UNARY_OPERATORS[unary_operator_type](operand)

        msg = f"Unsupported expression: {ast.dump(node, include_attributes=False)}"
        raise ValueError(msg)

    parsed = ast.parse(expression, mode="eval")
    return _evaluate(parsed)


@tool
def calculate(expression: str) -> float:
    """Evaluate arithmetic expressions using a constrained interpreter."""
    return _safe_arithmetic(expression)


@tool
def get_weather(location: str) -> dict:
    """Mock weather tool that returns fake weather data."""
    return {"location": location, "temperature": 72, "condition": "sunny", "humidity": 45}


def create_sample_prompt_files():
    """Create sample prompt files for demonstration."""
    # Create a custom ReactAgent prompt
    react_prompt = """I'm going to tip $100K for accurate, well-reasoned responses!

###Role###
You are a helpful assistant with access to tools.

###Available Tools###
{tools}

###Response Format###
You MUST respond with valid JSON. Choose ONE format:

1. Using a tool with reasoning:
{{"scratchpad": "Step-by-step thinking: [your analysis]", "tool": "tool_name", "arguments": {{"param": "value"}}}}

2. Providing final answer:
{{"scratchpad": "Based on the results: [your conclusion]", "answer": "Your comprehensive answer"}}

###Examples###
User: What's 15% of 200?
{{"scratchpad": "To find 15% of 200, I'll multiply 200 by 0.15", "tool": "calculate", "arguments": {{"expression": "200 * 0.15"}}}}

After tool returns 30:
{{"scratchpad": "The calculation shows 30, so 15% of 200 is 30", "answer": "15% of 200 is 30"}}

Think step by step. The better your reasoning and accuracy, the higher the tip!"""

    # Create a custom TinyCodeAgent prompt
    code_prompt = """###Role###
You are a Python code execution agent. Think step by step.

###Task###
Solve problems by writing Python code. Use ONLY these pre-imported tools:
{helpers}

###Requirements###
- Output ONLY a single Python code block
- Include clear reasoning as comments
- Call final_answer() with your result
- Think step by step

###Format###
```python
# Step 1: Understand the problem
# Step 2: Use available tools
output = tool_name(input_data)
# Step 3: Process output
# Step 4: Return final answer
final_answer(result)
```

Do NOT use print() for output. Do call final_answer() exactly once."""

    # Create temporary files
    temp_dir = tempfile.mkdtemp()
    react_prompt_file = Path(temp_dir) / "react_agent.prompt"
    code_prompt_file = Path(temp_dir) / "code_agent.prompt"

    react_prompt_file.write_text(react_prompt)
    code_prompt_file.write_text(code_prompt)

    return str(react_prompt_file), str(code_prompt_file), temp_dir


def demo_react_agent_with_prompt_file():
    """Demonstrate ReactAgent with custom prompt file."""
    print("\n" + "=" * 60)
    print("ReactAgent with Custom Prompt File")
    print("=" * 60)

    # Create sample prompt file
    react_prompt_file, code_prompt_file, temp_dir = create_sample_prompt_files()

    try:
        # Create ReactAgent with custom prompt file
        agent = ReactAgent(
            tools=[calculate, get_weather],
            prompt_file=react_prompt_file,
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        )

        print(f"✓ ReactAgent created with prompt file: {react_prompt_file}")
        print(f"✓ Custom prompt preview: {agent._system_prompt[:100]}...")

        # Note: In a real scenario, you would run the agent
        # result = agent.run("What's 15% of 200?")
        # print(f"Result: {result}")

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)


def demo_code_agent_with_prompt_file():
    """Demonstrate TinyCodeAgent with custom prompt file."""
    print("\n" + "=" * 60)
    print("TinyCodeAgent with Custom Prompt File")
    print("=" * 60)

    # Create sample prompt file
    react_prompt_file, code_prompt_file, temp_dir = create_sample_prompt_files()

    try:
        # Create TinyCodeAgent with custom prompt file
        agent = TinyCodeAgent(
            tools=[calculate],
            prompt_file=code_prompt_file,
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY", "test-key"),
        )

        print(f"✓ TinyCodeAgent created with prompt file: {code_prompt_file}")
        print(f"✓ Custom prompt preview: {agent._system_prompt[:100]}...")

        # Note: In a real scenario, you would run the agent
        # result = agent.run("Calculate 20% tip on $45")
        # print(f"Result: {result}")

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir)


def demo_fallback_behavior():
    """Demonstrate fallback behavior with missing/invalid files."""
    print("\n" + "=" * 60)
    print("Fallback Behavior Demo")
    print("=" * 60)

    # Create ReactAgent with missing prompt file (should fallback)
    agent1 = ReactAgent(
        tools=[calculate],
        prompt_file="nonexistent_file.txt",
        model="gpt-4o-mini",
        api_key="test-key",
    )

    print("✓ ReactAgent with missing prompt file - using default prompt")
    print(f"✓ Default prompt preview: {agent1._system_prompt[:100]}...")

    # Create TinyCodeAgent with no prompt file (should use default)
    agent2 = TinyCodeAgent(tools=[calculate], model="gpt-4o-mini", api_key="test-key")

    print("✓ TinyCodeAgent with no prompt file - using default prompt")
    print(f"✓ Default prompt preview: {agent2._system_prompt[:100]}...")


def demo_markdown_prompt():
    """Demonstrate using markdown files as prompts."""
    print("\n" + "=" * 60)
    print("Markdown Prompt File Demo")
    print("=" * 60)

    # Create a markdown prompt
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""# Custom Assistant Prompt

You are a helpful assistant with access to tools. Think step by step and provide clear answers.

## Available Tools
{tools}

## Instructions
- Show your reasoning
- Use tools when helpful
- Provide clear answers
- Be accurate

## Response Format
Respond with valid JSON containing your reasoning and either tool calls or final answer.
""")
        md_file = f.name

    try:
        # Create ReactAgent with markdown prompt
        agent = ReactAgent(
            tools=[calculate], prompt_file=md_file, model="gpt-4o-mini", api_key="test-key"
        )

        print(f"✓ ReactAgent created with markdown prompt: {md_file}")
        print(f"✓ Markdown prompt preview: {agent._system_prompt[:150]}...")

    finally:
        os.unlink(md_file)


def main():
    """Run all demonstrations."""
    print("File-Based Prompt Loading Demo")
    print("=" * 60)

    print("\nThis demo shows how to use custom prompt files with tinyAgent agents.")
    print("Prompt files can be .txt, .md, or .prompt files.")
    print("If a file is missing or invalid, agents fallback to default prompts.\n")

    # Run demonstrations
    demo_react_agent_with_prompt_file()
    demo_code_agent_with_prompt_file()
    demo_fallback_behavior()
    demo_markdown_prompt()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)

    print("\nKey Takeaways:")
    print("• Both ReactAgent and TinyCodeAgent support prompt_file parameter")
    print("• Supported file types: .txt, .md, .prompt")
    print("• Graceful fallback to default prompts when files are missing/invalid")
    print("• Perfect backward compatibility - no breaking changes")
    print("• Easy to customize agent behavior with simple text files")


if __name__ == "__main__":
    main()
