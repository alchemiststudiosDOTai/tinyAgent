#!/usr/bin/env python3
"""
Example 10: Boilerplate Tool Test

Demonstrates proper tool initialization and execution with correct imports.
"""

import os
import sys
from pathlib import Path

# Add project root to path (crucial for package resolution)
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from core.tools.boilerplate_tool import get_tool
from core.agent import Agent
from core.factory.agent_factory import AgentFactory
from core.logging import get_logger

logger = get_logger(__name__)

def main():
    """Test the boilerplate tool through an agent with proper initialization."""
    try:
        # Initialize agent factory
        factory = AgentFactory.get_instance()
        
        # Get the boilerplate tool instance
        boilerplate_tool = get_tool()
        
        # Create agent with the tool
        agent = factory.create_agent(
            tools=[boilerplate_tool],
            model="gpt-3.5-turbo"
        )
        
        # Test query with parameter validation
        test_input = "sample text for demonstration purposes"
        test_params = {
            "input_data": test_input,
            "max_items": 3
        }
        
        print(f"Testing {boilerplate_tool.name} tool:")
        print(f"Input: {test_input}")
        print(f"Parameters: {test_params}")
        
        # Execute the tool
        result = boilerplate_tool(**test_params)
        
        print("\nExecution successful!")
        print("Output:", result)
        
        return 0
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
