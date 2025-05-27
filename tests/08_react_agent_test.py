import json
import os

from tinyagent.react.react_agent import ReActAgent
from tinyagent.tools.g_login import get_tool


def test_react_agent_login():
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
    agent = ReActAgent(tools=[tool])

    result = agent.run_react("login", llm_callable=fake_llm)
    assert result == "done"
