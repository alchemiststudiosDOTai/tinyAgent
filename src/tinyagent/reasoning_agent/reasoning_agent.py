from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..tool import Tool


def default_llm(prompt: str) -> str:
    raise RuntimeError("No LLM callable provided")


@dataclass
class ThoughtStep:
    text: str


@dataclass
class ActionStep:
    tool: str
    args: Dict[str, Any]


@dataclass
class ObservationStep:
    result: Any


@dataclass
class Scratchpad:
    steps: List[Any] = field(default_factory=list)

    def add(self, step: Any) -> None:
        self.steps.append(step)

    def format(self) -> str:
        """Format the scratchpad for inclusion in prompts."""
        lines = []
        for step in self.steps:
            if isinstance(step, ThoughtStep):
                lines.append(f"Thought: {step.text}")
            elif isinstance(step, ActionStep):
                # Format action as JSON for consistency with expected format
                lines.append(
                    f"Action: {json.dumps({'tool': step.tool, 'args': step.args})}"
                )
            elif isinstance(step, ObservationStep):
                lines.append(f"Observation: {step.result}")
        return "\n".join(lines)


class ReasoningAgent:
    """Minimal agent implementing the reasoning and acting loop."""

    def __init__(self, tools: Optional[List[Tool]] = None):
        self.tools: Dict[str, Tool] = {}
        if tools:
            for tool in tools:
                self.register_tool(tool)

    def register_tool(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def execute_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        return self.tools[tool_name](**args)

    def run_reasoning(
        self,
        query: str,
        llm_callable: Optional[callable] = None,
        max_steps: int = 5,
        verbose: bool = False,
    ) -> Any:
        from ..utils.json_parser import robust_json_parse

        llm = llm_callable or default_llm
        scratchpad = Scratchpad()
        step_count = 0

        for _ in range(max_steps):
            step_count += 1
            if verbose:
                print(f"\n{'=' * 60}")
                print(f"STEP {step_count}")
                print(f"{'=' * 60}")

            prompt = self._build_prompt(query, scratchpad)

            if verbose:
                print("\n📝 SCRATCHPAD:")
                if scratchpad.steps:
                    for step in scratchpad.steps:
                        if isinstance(step, ThoughtStep):
                            print(f"  💭 Thought: {step.text}")
                        elif isinstance(step, ActionStep):
                            print(f"  🔧 Action: {step.tool}({step.args})")
                        elif isinstance(step, ObservationStep):
                            print(f"  👁️  Observation: {step.result}")
                else:
                    print("  (empty)")

                print("\n📄 FULL PROMPT BEING SENT:")
                print("-" * 40)
                print(prompt)
                print("-" * 40)
                print("\n⏳ Calling LLM...")

            content = llm(prompt)

            if verbose:
                print(f"\n📥 LLM Response: {content[:200]}...")

            # Use the framework's robust JSON parser
            data = robust_json_parse(content, expected_keys=["thought", "action"])
            if not data:
                data = {}

            if verbose and data:
                print(f"\n✅ Parsed JSON:")
                print(f"  💭 Thought: {data.get('thought', 'N/A')}")
                if data.get("action"):
                    print(f"  🔧 Action: {data['action'].get('tool', 'N/A')}")
                    print(f"  📋 Args: {data['action'].get('args', {})}")

            thought = data.get("thought", "")
            if thought:
                scratchpad.add(ThoughtStep(thought))

            action = data.get("action")
            if not action:
                # If no action, assume final answer
                final = data.get("final_answer")
                if final is not None:
                    return final
                return data

            tool_name = action.get("tool")
            args = action.get("args", {})

            if tool_name == "final_answer":
                if verbose:
                    print(f"\n🎯 Final Answer: {args.get('answer')}")
                return args.get("answer")

            scratchpad.add(ActionStep(tool=tool_name, args=args))

            if verbose:
                print(f"\n🔨 Executing tool: {tool_name}({args})")

            result = self.execute_tool_call(tool_name, args)
            scratchpad.add(ObservationStep(result=result))

        return None

    def _build_prompt(self, query: str, scratchpad: Scratchpad) -> str:
        # Format available tools
        tools_desc = []
        for name, tool in self.tools.items():
            tools_desc.append(f"- {name}: {tool.description}")

        instructions = (
            "You are a reasoning agent. Use a Thought -> Action -> Observation loop.\n\n"
            "Available tools:\n" + "\n".join(tools_desc) + "\n"
            "- final_answer: Provide the final answer to the query\n\n"
            'Respond ONLY with JSON in the form {"thought": str, '
            '"action": {"tool": str, "args": {...}}} or, to finish, '
            '{"thought": str, "action": {"tool": "final_answer", '
            '"args": {"answer": str}}}.'
        )
        pad = scratchpad.format()
        if pad:
            instructions += "\n\nPrevious steps:\n" + pad
        instructions += f"\n\nUser query: {query}\nThought:"
        return instructions
