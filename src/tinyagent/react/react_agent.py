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
        lines = []
        for step in self.steps:
            if isinstance(step, ThoughtStep):
                lines.append(f"Thought: {step.text}")
            elif isinstance(step, ActionStep):
                lines.append(
                    f"Action: {json.dumps({'tool': step.tool, 'args': step.args})}"
                )
            elif isinstance(step, ObservationStep):
                lines.append(f"Observation: {step.result}")
        return "\n".join(lines)

class ReActAgent:
    """Minimal agent implementing the ReAct loop."""

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

    def run_react(
        self,
        query: str,
        llm_callable: Optional[callable] = None,
        max_steps: int = 5,
    ) -> Any:
        llm = llm_callable or default_llm
        scratchpad = Scratchpad()

        for _ in range(max_steps):
            prompt = self._build_prompt(query, scratchpad)
            content = llm(prompt)
            try:
                data = json.loads(content)
            except Exception:
                data = {}

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
                return args.get("answer")

            scratchpad.add(ActionStep(tool=tool_name, args=args))
            result = self.execute_tool_call(tool_name, args)
            scratchpad.add(ObservationStep(result=result))

        return None

    def _build_prompt(self, query: str, scratchpad: Scratchpad) -> str:
        instructions = (
            "You are a ReAct agent. Use a Thought -> Action -> Observation loop. "
            "Respond ONLY with JSON in the form {\"thought\": str, "
            "\"action\": {\"tool\": str, \"args\": {...}}} or, to finish, "
            "{\"thought\": str, \"action\": {\"tool\": \"final_answer\", "
            "\"args\": {\"answer\": str}}}."
        )
        pad = scratchpad.format()
        if pad:
            instructions += "\nPrevious steps:\n" + pad
        instructions += f"\nUser query: {query}\nThought:"
        return instructions

