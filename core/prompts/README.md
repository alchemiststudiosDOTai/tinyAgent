# Prompt Templates for tinyAgent

This directory contains prompt templates that can be used with the tinyAgent framework. The templates are written in Markdown format and can include variable placeholders.

## Directory Structure

```
core/prompts/
├── system/           # System-level prompts
│   ├── agent.md     # Main agent system prompt
│   ├── retry.md     # Retry prompt
│   └── strict_json.md # Strict JSON mode prompt
├── tools/           # Tool-specific prompts
│   ├── calculator.md
│   └── weather.md
├── workflows/       # Workflow-specific prompts
│   ├── triage.md
│   └── phased.md
└── README.md        # This file
```

## Invest in learning to prompt

Prompt engineering is a valuable skill that can significantly improve the quality of your agent responses. Consider these resources to enhance your prompt writing skills:

- [LLMKit-rs](https://github.com/danwritecode/llmkit-rs) - A Rust toolkit for building LLM applications with useful prompt patterns
- [Prompting Guide](https://arxiv.org/html/2312.16171v1) - Academic research on effective prompt engineering techniques

## Using Templates in Your Code

### Basic Usage

You can reference templates in your code using the `{{template_name}}` syntax:

```python
from core.agent import Agent
from core.factory.agent_factory import AgentFactory

# Create agent
factory = AgentFactory.get_instance()
agent = Agent(factory=factory)

# Use a template with the {{template_name}} syntax
result = agent.run(
    query="What is the weather in New York?",
    template_path="{{weather}}"  # References core/prompts/tools/weather.md
)
```

### Using Templates with Variables

Templates can include variable placeholders in the format `{{variable_name}}`. When running your agent, you can provide values for these variables:

```python
# Define variables to substitute in the template
variables = {
    "location": "San Francisco",
    "date": "2025-03-17",
    "units": "Celsius"
}

# Use template with variables
result = agent.run(
    query="What's the weather forecast?",
    template_path="{{weather}}",  # References core/prompts/tools/weather.md
    variables=variables
)
```

## Creating New Templates

### Template Format

Templates are text files (typically markdown) with special placeholders for variables:

```markdown
# Weather Query Template

Please provide weather information for {{location}} on {{date}}.
The user's query is: {{query}}

Additional preferences:
- Temperature units: {{units}}
```

### Special Variables

The `{{query}}` variable is automatically populated with the query string provided to `agent.run()`, but you can override it by including it in your variables dictionary.

### Naming Convention

Template files should:
1. Use lowercase names
2. Use underscores for spaces
3. Have the `.md` extension
4. Be placed in the appropriate subdirectory based on its purpose:
   - `system/` for system-level prompts
   - `tools/` for tool-specific prompts
   - `workflows/` for workflow-specific prompts

For example: `weather_forecast.md`, `code_generation.md`, `data_analysis.md`

## Example Template Structure

Here's a recommended structure for complex templates:

```markdown
# Template Name

## Context
Background information and context for the AI.

## Instructions
Specific instructions for how to process this query.

## User Query
{{query}}

## Additional Information
- Parameter 1: {{param1}}
- Parameter 2: {{param2}}

## Response Format
Instructions on how the response should be formatted.
```

## Tips for Effective Templates

1. **Be specific**: Give clear instructions about what you want the agent to do
2. **Provide context**: Include any relevant context that might help the agent understand the query
3. **Define scope**: Clearly define the boundaries of what the agent should and shouldn't do
4. **Use variables**: Make your templates reusable by parameterizing the parts that change
5. **Format strategically**: Use markdown formatting to emphasize important parts of the prompt
