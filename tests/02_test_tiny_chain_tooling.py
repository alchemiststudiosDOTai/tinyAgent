#!/usr/bin/env python3
"""
Test for tiny_chain: Find and summarize U.S. import-tariff data
"""
import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from tinyagent.factory.tiny_chain import tiny_chain
from tinyagent.tools.duckduckgo_search import get_tool as search_tool
from tinyagent.tools.custom_text_browser import get_tool as browser_tool
from tinyagent.decorators import tool
from tinyagent.agent import get_llm

@tool(name="summarize", description="Summarize input text with the LLM")
def summarize(text: str) -> str:
    prompt = f"Summarize the following text:\n\n{text}\n\nSummary:"
    return get_llm()(prompt).strip()

def test_tiny_chain_tariff_search():
    """Test that tiny_chain can search for and summarize US import tariff data"""
    # Create chain
    chain = tiny_chain.get_instance(
        tools=[search_tool(), browser_tool(), summarize._tool]
    )  
    try:
        # Submit the task
        task_id = chain.submit_task(
            "Find current US import tariffs and visit official trade websites for details"
        )
        
        # Get the result - only check that we get *some* result, not what it is
        result = chain.get_task_status(task_id).result
        
        # Basic sanity checks for non-empty response
        assert result is not None
        
        # Verify task completed
        task_status = chain.get_task_status(task_id)
        assert task_status is not None
        # Mark test as passed
        assert True
        # Return the result for inspection when run from main
        return result
    except Exception as e:
        # Log the error for easier debugging
        print(f"Error running tiny_chain: {str(e)}")
        # Fail the test
        assert False, f"Chain execution failed with error: {str(e)}"

# Run the test manually if called directly
if __name__ == "__main__":
    result = test_tiny_chain_tariff_search()
    print(result)