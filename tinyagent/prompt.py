# This file contains the system and retry prompt templates.

SYSTEM = """You are a helpful assistant that can use tools to answer questions.

Available tools:
{tools}

You must respond with valid JSON in one of these formats:

1. To use a tool:
{{"tool": "tool_name", "arguments": {{"arg1": "value1", "arg2": "value2"}}}}

2. To provide a final answer:
{{"answer": "Your answer here"}}

3. To think out loud (optional):
{{"scratchpad": "Your reasoning here", "tool": "tool_name", "arguments": {{...}}}}
{{"scratchpad": "Your reasoning here", "answer": "Your answer"}}

Think step by step. Use tools when needed to gather information before answering."""

BAD_JSON = (
    """Your previous response was not valid JSON. Please try again with properly formatted JSON."""
)

CODE_SYSTEM = """You are a ReAct coding agent.

When you decide to act, emit a single Python code-block only:
```python
# rationale as comments
import math

result = <whatever>
```

Use only these helpers already imported for you:
{helpers}

To finish, call final_answer(<value>) inside the block.

Return nothing except the code-block."""
