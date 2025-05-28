import json
import os

from tinyagent import ReactAgent
from tinyagent.tools.g_login import get_tool


def test_react_agent_login():
    responses = [
        """Thought: Need credentials to login
Action: g_login
Action Input: {"username": "foo", "password": "bar"}""",
        """Thought: Login complete, returning final answer
Action: final_answer
Action Input: {"answer": "done"}"""
    ]

    def fake_llm(_prompt):
        return responses.pop(0)

    tool = get_tool()
    agent = ReactAgent(tools=[tool])

    result = agent.run("login", llm_callable=fake_llm)
    assert result == "done"
