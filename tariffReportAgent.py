#!/usr/bin/env python3
"""
Tariff Report Agent Example (Best Practice)

Demonstrates:
- Using the enhanced_deepsearch tool via the @tool-decorated wrapper (best practice)
- Registering a random summarizer tool (@tool)
- Using the file_manipulator_tool to save results
- Best practices with the Factory Pattern
"""

import sys
import os
import random
from pprint import pprint

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tinyagent.factory.agent_factory import AgentFactory
from tinyagent.tools.enhanced_deepsearch import enhanced_deepsearch_tool_wrapper
from tinyagent.tools import file_manipulator_tool
from tinyagent.decorators import tool

@tool
def random_summary_tool(report: str) -> str:
    """
    Randomly summarizes the report by picking a few sentences.
    """
    sentences = [s.strip() for s in report.replace('\n', '. ').split('.') if len(s.strip()) > 20]
    if not sentences:
        return "No content to summarize."
    summary = " ".join(random.sample(sentences, min(3, len(sentences))))
    return f"Random Summary:\n{summary}"

def main():
    print("Tariff Report Agent Example (Best Practice)")
    print("------------------------------------------")

    # --- Factory Pattern: Register tools ---
    factory = AgentFactory.get_instance()
    # Register the @tool-decorated enhanced_deepsearch tool (best practice)
    factory.register_tool(enhanced_deepsearch_tool_wrapper._tool)
    factory.register_tool(random_summary_tool._tool)
    factory.register_tool(file_manipulator_tool)

    agent = factory.create_agent()

    # --- 1. Use enhanced_deepsearch via the agent (best practice) ---
    query = "Generate a research report on current global tariffs"
    print(f"\n[Agent] Running enhanced_deepsearch on: {query}")
    result = agent.run(
        "Use the enhanced_deepsearch tool to research tariffs",
        variables={"query": query, "max_steps": 2}
    )
    print("\n[Agent] enhanced_deepsearch result (truncated):")
    pprint(result)

    # --- 2. Use the file tool to save the full report ---
    report_content = str(result)
    save_result = agent.run(
        "Create a file named 'tinyAgent_output/tariff_report.json' with the research results",
        variables={
            "operation": "create",
            "path": "tinyAgent_output/tariff_report.json",
            "content": report_content
        }
    )
    print("\n[Agent] Report saved to tinyAgent_output/tariff_report.json")

    # --- 3. Use the random summary tool to summarize the report ---
    summary = agent.run(
        "Summarize the research report using the random summary tool",
        variables={"report": report_content}
    )
    print("\n[Agent] Random summary:")
    print(summary)

    # --- 4. Save the summary to a file ---
    agent.run(
        "Create a file named 'tinyAgent_output/tariff_report_summary.txt' with the summary",
        variables={
            "operation": "create",
            "path": "tinyAgent_output/tariff_report_summary.txt",
            "content": summary
        }
    )
    print("\n[Agent] Summary saved to tinyAgent_output/tariff_report_summary.txt")

if __name__ == "__main__":
    main()
    print("\n[Agent] Summary saved to tinyAgent_output/tariff_report_summary.txt")

if __name__ == "__main__":
    main()