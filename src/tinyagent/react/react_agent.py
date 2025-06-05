from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..agent import get_llm
from ..prompts.prompt_manager import PromptManager
from ..tool import Tool

DEFAULT_REACT_SYSTEM_PROMPT = (
    "You are a helpful assistant that can use tools to answer questions."
)


def default_llm(prompt: str) -> str:
    raise RuntimeError("No LLM callable provided")


@dataclass
class ThoughtStep:
    text: str


@dataclass
class ActionStep:
    tool: str
    args: dict[str, Any]


@dataclass
class ObservationStep:
    result: Any


@dataclass
class Scratchpad:
    steps: list[Any] = field(default_factory=list)

    def add(self, step: Any) -> None:
        self.steps.append(step)

    def format(self) -> str:
        lines = []
        for step in self.steps:
            if isinstance(step, ThoughtStep):
                lines.append(f"Thought: {step.text}")
            elif isinstance(step, ActionStep):
                lines.append(f"Action: {step.tool}")
                lines.append(f"Action Input: {json.dumps(step.args)}")
            elif isinstance(step, ObservationStep):
                lines.append(f"Observation: {step.result}")
        return "\n".join(lines)


class FinalAnswerCalled(Exception):
    """Exception raised when final_answer() is called to signal completion."""

    def __init__(self, answer):
        self.answer = answer
        super().__init__(f"Final answer: {answer}")


@dataclass
class ReactAgent:
    """ReAct (Reasoning + Acting) agent with built-in LLM support."""

    tools: list[Tool] = field(default_factory=list)
    llm_callable: callable | None = None
    max_steps: int = 10
    add_base_tools: bool = True
    system_prompt: str | None = None
    system_template: str | None = None
    prompt_manager: PromptManager = field(
        default_factory=PromptManager, init=False, repr=False
    )

    def __post_init__(self):
        if self.llm_callable is None:
            self.llm_callable = get_llm()

        # Process tools if they were passed as decorated functions
        processed_tools = []
        for tool in self.tools:
            if hasattr(tool, "_tool"):
                # This is a decorated function, extract the Tool object
                processed_tools.append(tool._tool)
            elif isinstance(tool, Tool):
                # This is already a Tool object
                processed_tools.append(tool)
            else:
                # Try to convert it to a tool
                from ..decorators import tool as tool_decorator

                decorated = tool_decorator(tool)
                processed_tools.append(decorated._tool)

        self.tools = processed_tools

        # Add the built-in final_answer function as a tool if requested
        if self.add_base_tools:
            self._add_final_answer_tool()

    def _add_final_answer_tool(self):
        """Add the built-in final_answer function as a tool."""

        def final_answer_func(answer: Any) -> str:
            """Call this function when you have the final answer to return to the user.

            Args:
                answer: The final answer to return (can be a number, string, or any result)
            """
            # Raise a special exception to signal completion
            raise FinalAnswerCalled(answer)

        # Create the tool manually to avoid circular imports
        final_answer_tool = Tool(
            func=final_answer_func,
            name="final_answer",
            description="Call this function when you have the final answer to return to the user.",
            parameters={
                "answer": {
                    "type": "any",
                    "description": "The final answer to return (can be a number, string, or any result)",
                }
            },
        )

        self.tools.append(final_answer_tool)

    def register_tool(self, tool: Any) -> None:
        """Register a tool with the agent.

        Args:
            tool: Can be a Tool object, a decorated function with ._tool attribute,
                  or a plain function that will be converted to a tool.
        """
        if hasattr(tool, "_tool"):
            # This is a decorated function, extract the Tool object
            self.tools.append(tool._tool)
        elif isinstance(tool, Tool):
            # This is already a Tool object
            self.tools.append(tool)
        else:
            # Try to convert it to a tool
            from ..decorators import tool as tool_decorator

            decorated = tool_decorator(tool)
            self.tools.append(decorated._tool)

    def _load_system_prompt(self) -> str:
        """Load the base system prompt for the agent."""
        if self.system_prompt:
            return self.system_prompt
        if self.system_template:
            try:
                return self.prompt_manager.load_template(
                    f"system/{self.system_template}.md"
                )
            except Exception:
                pass
        return DEFAULT_REACT_SYSTEM_PROMPT

    def get_tool_descriptions(self) -> str:
        """Get formatted descriptions of all available tools."""
        descriptions = []
        for tool in self.tools:
            descriptions.append(f"{tool.name}: {tool.description}")
        return "\n".join(descriptions)

    def parse_action(self, text: str) -> ActionStep | None:
        """Parse action from LLM response."""
        lines = text.strip().split("\n")
        action_line = None
        input_line = None

        for line in lines:
            if line.startswith("Action:"):
                action_line = line[7:].strip()
            elif line.startswith("Action Input:"):
                input_line = line[13:].strip()

        if action_line and input_line:
            try:
                args = json.loads(input_line)
                return ActionStep(tool=action_line, args=args)
            except json.JSONDecodeError:
                return None
        return None

    def execute_tool(self, action: ActionStep) -> Any:
        """Execute a tool action."""
        for tool in self.tools:
            if tool.name == action.tool:
                try:
                    # Special handling for final_answer tool
                    if tool.name == "final_answer":
                        # Extract the answer from the arguments
                        if isinstance(action.args, dict) and "answer" in action.args:
                            answer = action.args["answer"]
                        else:
                            # If args is not a dict or doesn't have "answer" key, use the whole args
                            answer = action.args
                        raise FinalAnswerCalled(answer) from None
                    else:
                        return tool(**action.args)
                except FinalAnswerCalled as e:
                    # Re-raise to be caught at the higher level
                    raise e
                except Exception as e:
                    return f"Error executing {tool.name}: {str(e)}"
        return f"Tool '{action.tool}' not found"

    def run(
        self,
        query: str,
        max_steps: int | None = None,
        llm_callable: callable | None = None,
    ) -> str:
        """Run the agent with the given query. Alias for run_react for better ergonomics."""
        return self.run_react(query, max_steps, llm_callable)

    def run_react(
        self,
        query: str,
        max_steps: int | None = None,
        llm_callable: callable | None = None,
    ) -> str:
        """Run the ReAct reasoning loop."""
        if max_steps is None:
            max_steps = self.max_steps

        # Use provided llm_callable for testing, otherwise use the instance's
        llm = llm_callable if llm_callable is not None else self.llm_callable

        scratchpad = Scratchpad()

        for step in range(max_steps):
            print(f"\n{'='*50}")
            print(f"STEP {step + 1}")
            print(f"{'='*50}")

            # Create prompt with current scratchpad
            prompt = self._create_prompt(query, scratchpad)

            # Get LLM response
            print("Calling LLM...")
            response = llm(prompt)
            print("\nLLM Response:")
            print(f"'{response}'")

            # Parse thought
            if "Thought:" in response:
                thought_text = (
                    response.split("Thought:")[-1].split("Action:")[0].strip()
                )
                scratchpad.add(ThoughtStep(thought_text))
                print(f"\nTHOUGHT: {thought_text}")

            # Parse and execute action
            action = self.parse_action(response)
            if action:
                print(f"\nACTION: {action.tool}")
                print(f"INPUT: {json.dumps(action.args)}")
                scratchpad.add(action)

                try:
                    result = self.execute_tool(action)
                    print(f"RESULT: {result}")
                    scratchpad.add(ObservationStep(result))
                except FinalAnswerCalled as e:
                    # Final answer was called - return it directly
                    print("\n*** FINAL ANSWER CALLED ***")
                    print(f"Answer: {e.answer}")
                    return str(e.answer)
            else:
                # If no valid action found, this might be a final answer in text form
                print("\nNo valid action found, treating as final answer")
                # Just return the response as-is since the LLM didn't use the final_answer tool
                return response.strip()

            # Show current scratchpad
            print("\n--- SCRATCHPAD SO FAR ---")
            scratchpad_content = scratchpad.format()
            if scratchpad_content:
                print(scratchpad_content)
            else:
                print("(empty)")
            print("--- END SCRATCHPAD ---")

        return "Maximum steps reached without final answer"

    def _create_prompt(self, query: str, scratchpad: Scratchpad) -> str:
        """Create the ReAct prompt."""
        tools_desc = self.get_tool_descriptions()
        system_prompt = self._load_system_prompt()

        prompt = f"""{system_prompt}

Available tools:
{tools_desc}

Use the following format:
Thought: think about what to do
Action: the action to take (must be one of the available tools)
Action Input: the input to the action as valid JSON

IMPORTANT:
- Only provide ONE Thought and ONE Action at a time
- Do NOT generate Observations - I will provide the real observation after executing your action
- Do NOT continue with more thoughts/actions after your first action
- When you have the final answer, use the final_answer tool like this:
  Action: final_answer
  Action Input: {{"answer": "your answer here"}}

Question: {query}

{scratchpad.format()}"""
        return prompt
