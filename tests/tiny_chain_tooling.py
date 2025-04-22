#!/usr/bin/env python3
"""
tiny_chain example: automatically find and summarise U.S. import-tariff data
"""
from tinyagent.factory.tiny_chain import tiny_chain
from tinyagent.tools.duckduckgo_search import get_tool as search_tool
from tinyagent.tools.custom_text_browser import get_tool as browser_tool
from tinyagent.decorators import tool
from tinyagent.agent import get_llm

@tool(name="summarize", description="Summarize input text with the LLM")
def summarize(text: str) -> str:
    prompt = f"Summarize the following text:\n\n{text}\n\nSummary:"
    return get_llm()(prompt).strip()

# 1 – build the chain
chain = tiny_chain.get_instance(
    tools=[search_tool(), browser_tool(), summarize._tool]
)

# 2 – submit any natural-language task
task_id = chain.submit_task(
    "Find current US import tariffs and visit official trade websites for details"
)

# 3 – get structured results
print(chain.get_task_status(task_id).result)