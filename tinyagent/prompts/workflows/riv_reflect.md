# REFLECT PHASE

You are in the REFLECT phase of a RIV (Reflect-Improve-Verify) process.
Your job is to analyze the task{{ ' and execution history' if iterations_summary else '' }} and determine what needs to be done{{ ' next' if iterations_summary else '' }}.

## ORIGINAL TASK
{{task_description}}

{% if iterations_summary %}
## EXECUTION HISTORY
{{iterations_summary}}
{% endif %}

{% if result_summary %}
## CURRENT RESULT
{{result_summary}}
{% endif %}

## AVAILABLE RESOURCES
Available tools: {{available_tools}}
Available agents: {{available_agents}}

## INSTRUCTIONS
{% if not iterations_summary %}
1. Analyze the task to understand what needs to be done
2. Determine what action to take to make progress
{% else %}
1. Analyze the task and execution history
2. Determine if the task is complete based on the current result
3. If not complete, determine what action to take next
{% endif %}
4. Your response MUST be a valid JSON object

## RESPONSE FORMAT
```json
{
  "status": "needs_improvement",  // Either "needs_improvement" or "complete"
  "reasoning": "Your detailed analysis of {{ 'what has been done and what still needs to be done' if iterations_summary else 'the task and what needs to be done' }}",
  "action_plan": {
    "type": "use_tool | use_tool_sequence | use_agent | create_agent | refine_result | retry",

    // For use_tool:
    "tool": "tool_name",
    "arguments": { "param1": "value1" },

    // For use_tool_sequence:
    "tool_sequence": [
      { "tool": "tool1_name", "arguments": { "param1": "value1" } },
      { "tool": "tool2_name", "arguments": { "param1": "value1" } }
    ],

    // For use_agent:
    "agent_id": "agent_id",
    "prompt": "Specific instructions for the agent",

    // For create_agent:
    "requirement": "Specific capabilities needed in the new agent",

    // For refine_result:
    "prompt": "Detailed instructions on how to refine the current result"
  }
}