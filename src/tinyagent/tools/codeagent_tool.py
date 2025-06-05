"""
CodeAgent Tool for the tinyAgent Framework
Heavily inspired by smolagents and other open-research(ms) agent projects

This tool allows an LLM to generate and execute Python code in a sandboxed
environment. The agent can call upon existing tinyAgent tools (like web
search, summarization, entity extraction, etc.) by referencing them in code
(e.g. 'search_web("some query")' or 'summarize_text("some text")').

It is primarily aimed at enabling sophisticated, code-centric reasoning
and dynamic orchestration of tasks.
"""

import re
import traceback
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..agent import get_llm
from ..config import load_config
from ..logging import get_logger
from ..tool import ParamType, Tool
from .anon_coder import execute_python_code

# Set up logger
logger = get_logger(__name__)


class CodeGenerationMode(Enum):
    """Different modes for code generation."""

    BASIC = "basic"  # Simple code generation
    ADVANCED = "advanced"  # With tool integration
    RESEARCH = "research"  # With web search and analysis


@dataclass
class CodeGenerationContext:
    """Context for code generation including memory and tools."""

    memory: str = ""
    available_tools: List[str] = None
    mode: CodeGenerationMode = CodeGenerationMode.BASIC
    max_iterations: int = 3
    timeout: int = 15

    def __post_init__(self):
        if self.available_tools is None:
            self.available_tools = []


def generate_system_prompt(context: CodeGenerationContext, task: str) -> str:
    """Generate the system prompt for the LLM."""
    tools_description = (
        "\n".join(
            [
                f"- {tool}() -> returns {tool} results"
                for tool in context.available_tools
            ]
        )
        if context.available_tools
        else "No tools available"
    )

    return f"""\
You are an autonomous CodeAgent heavily inspired by smolagents.
You write Python code to solve the task at hand, using built-in or
allowed libraries. If relevant, you can call tinyAgent utility functions:

{tools_description}

Your constraints and guidelines:
- Only return Python code with minimal explanation
- No dangerous imports (os, sys, subprocess, etc.)
- Keep all code in a single code block with NO triple backticks
- If you need to store intermediate results in variables, do so
- Maximum {context.max_iterations} iterations for loops
- Handle errors gracefully with try/except blocks
- Use type hints for better code quality

Context memory:
\"\"\"{context.memory}\"\"\"

Task to solve:
\"\"\"{task}\"\"\"

Write only Python code:"""


def validate_generated_code(code: str) -> bool:
    """Validate the generated code for security and quality."""
    # Check for dangerous operations
    dangerous_patterns = [
        r"exec\s*\(",
        r"eval\s*\(",
        r"os\.",
        r"sys\.",
        r"subprocess\.",
        r"__import__\s*\(",
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, code):
            logger.warning(f"Dangerous operation detected: {pattern}")
            return False

    # Check for basic syntax
    try:
        compile(code, "<string>", "exec")
        return True
    except SyntaxError as e:
        logger.error(f"Syntax error in generated code: {str(e)}")
        return False


def code_agent_execute(
    task: str,
    context_memory: Optional[str] = "",
    timeout: int = 15,
    mode: str = "basic",
    available_tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    The CodeAgent tool will:
      1. Prompt the LLM to produce Python code to solve 'task'
      2. Validate and sanitize the generated code
      3. Execute that code with a safe Python runner
      4. Return the code + the result to the caller

    Args:
        task: High-level instruction or partial plan
        context_memory: Optional string memory for continuity
        timeout: Execution time limit (seconds)
        mode: Code generation mode (basic/advanced/research)
        available_tools: List of available tool names

    Returns:
        Dict containing:
        - generated_code: The generated Python code
        - execution_result: The execution output
        - success: Whether execution was successful
        - error: Any error message if failed
    """
    try:
        # Load configuration
        config = load_config()
        model = config.get("model", {}).get("default", "gpt-3.5-turbo")
        llm = get_llm(model)

        # Set up context
        context = CodeGenerationContext(
            memory=context_memory,
            available_tools=available_tools or [],
            mode=CodeGenerationMode(mode),
            timeout=timeout,
        )

        # Generate code
        logger.debug("[CodeAgent] Prompting LLM to generate code for task")
        system_prompt = generate_system_prompt(context, task)
        generated_code = llm(system_prompt).strip()

        if not generated_code:
            return {
                "success": False,
                "error": "No code generated",
                "generated_code": "",
                "execution_result": "",
            }

        # Validate code
        if not validate_generated_code(generated_code):
            return {
                "success": False,
                "error": "Generated code failed validation",
                "generated_code": generated_code,
                "execution_result": "",
            }

        # Execute code
        logger.debug("[CodeAgent] Executing generated code in sandbox")
        execution_output = execute_python_code(code=generated_code, timeout=timeout)

        return {
            "success": True,
            "generated_code": generated_code,
            "execution_result": execution_output,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Error in code_agent_execute: {str(e)}\n{traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "generated_code": "",
            "execution_result": "",
        }


# Create tool instance
codeagent_tool = Tool(
    name="code_agent",
    description=(
        "A code-centric agent tool that prompts an LLM to write Python code for a given 'task' "
        "and executes it safely in a sandbox. Heavily inspired by smolagents and open research "
        "agent frameworks like smolGPT, allowing dynamic orchestration via code actions."
    ),
    parameters={
        "task": ParamType.STRING,
        "context_memory": ParamType.STRING,
        "timeout": ParamType.INTEGER,
        "mode": ParamType.STRING,
        "available_tools": ParamType.LIST,
    },
    func=code_agent_execute,
)


def get_tool() -> Tool:
    """
    Return the code agent tool instance for tinyAgent integration.

    Returns:
        Tool: The code_agent Tool object
    """
    return codeagent_tool
