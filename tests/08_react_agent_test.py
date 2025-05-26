import json
import os

from tinyagent.reasoning_agent.reasoning_agent import ReasoningAgent
from tinyagent.tools.g_login import get_tool


def test_reasoning_agent_login():
    responses = [
        json.dumps({
            "thought": "Need credentials to login",
            "action": {"tool": "g_login", "args": {"username": "foo", "password": "bar"}}
        }),
        json.dumps({
            "thought": "Login complete",
            "action": {"tool": "final_answer", "args": {"answer": "done"}}
        })
    ]

    def fake_llm(_prompt):
        return responses.pop(0)

    tool = get_tool()
    agent = ReasoningAgent(tools=[tool])

    result = agent.run_reasoning("login", llm_callable=fake_llm)
    assert result == "done"
