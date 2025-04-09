# tinyAgent Retry Prompt

Your previous response was invalid. Please respond with a valid JSON object in ONE of these formats:

## Option 1 - Tool Execution Format:
```json
{
    "tool": "tool_name",
    "arguments": {
        "arg1": "value1",
        "arg2": "value2"
    }
}
```

## Option 2 - Triage Assessment Format:
```json
{
    "assessment": "direct|delegate|create_new|phased",
    "agent_id": "agent_id_if_delegating",
    "requires_new_agent": true/false,
    "reasoning": "Your reasoning for this decision"
}
```

Available tools:
{{tools}}

CRITICAL RULES:
1. Response MUST be a valid JSON object
2. For Option 1: The "tool" field must be one of the available tools listed above
3. For Option 1: The "arguments" field must contain all required parameters for the selected tool
4. For Option 2: The "assessment" field must be one of the specified values
5. DO NOT include any text outside the JSON object
6. DO NOT use markdown formatting or code blocks in the response
7. ONLY respond with the raw JSON object

Example valid responses:
```json
{
    "tool": "calculator",
    "arguments": {
        "expression": "5 + 3"
    }
}
```

OR

```json
{
    "assessment": "direct",
    "requires_new_agent": false,
    "reasoning": "This task can be handled directly with existing tools"
}
