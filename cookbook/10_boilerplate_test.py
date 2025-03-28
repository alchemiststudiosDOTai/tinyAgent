#!/usr/bin/env python3
"""
Example 10: Boilerplate Tool Test

Demonstrates proper tool initialization and execution with correct imports.
"""

import sys
import os

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools.boilerplate_tool import get_tool
from core.factory.agent_factory import AgentFactory
from core.logging import get_logger

logger = get_logger(__name__)


def main():
    """Test the boilerplate tool through an agent with proper initialization."""
    print("Boilerplate Tool Example")
    print("------------------------")
    print("This example demonstrates using the boilerplate tool through")
    print("the agent framework with proper initialization.")
    print()

    try:
        # Get the singleton factory instance
        factory = AgentFactory.get_instance()

        # Register the boilerplate tool
        factory.register_tool(get_tool())

        # Create an agent using the factory
        agent = factory.create_agent()

        # Test query with parameter validation
        test_input = "sample text for demonstration purposes"
        test_params = {"input_data": test_input, "max_items": 3}

        print(f"Testing boilerplate tool:")
        print(f"Input: {test_input}")
        print(f"Parameters: {test_params}")

        # Execute through agent.run()
        result = agent.run(
            "Process input data using boilerplate tool",
            variables=test_params
        )

        print("\nExecution successful!")
        print("Output:", result)

        return 0

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
