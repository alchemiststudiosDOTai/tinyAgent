#!/usr/bin/env python3
"""
Example 10: Boilerplate Tool Test with ElderBrain

Demonstrates proper tool initialization and execution with ElderBrain integration.
"""

import sys
import os
from typing import Dict, Any

# Add project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools.boilerplate_tool import get_tool
from core.factory.agent_factory import AgentFactory
from core.factory.elder_brain import ElderBrain
from core.logging import get_logger

logger = get_logger(__name__)

def create_elder_brain_agent() -> ElderBrain:
    """Create and configure an ElderBrain instance with boilerplate tool."""
    factory = AgentFactory.get_instance()
    factory.register_tool(get_tool())
    agent = factory.create_agent()
    return ElderBrain(agent)

def process_with_elder_brain(eb: ElderBrain, input_data: str) -> Dict[str, Any]:
    """Process input using ElderBrain's three-phase approach."""
    # Phase 1: Information Gathering
    context = eb.gather_information(
        f"Process this input: {input_data}",
        variables={"input_data": input_data, "max_items": 3}
    )
    
    # Phase 2: Solution Planning
    plan = eb.plan_solution(
        "Plan how to process the input data",
        context=context
    )
    
    # Phase 3: Execution
    return eb.execute_solution(
        "Execute the processing plan",
        plan=plan
    )

def main():
    """Test the boilerplate tool through ElderBrain with proper initialization."""
    print("Boilerplate Tool with ElderBrain Example")
    print("---------------------------------------")
    print("This demonstrates using the boilerplate tool through")
    print("ElderBrain's three-phase processing approach.")
    print()

    try:
        # Create ElderBrain instance
        eb = create_elder_brain_agent()
        
        # Test input
        test_input = "sample text for demonstration purposes"
        print(f"Testing boilerplate tool with input: {test_input}")

        # Process through ElderBrain
        result = process_with_elder_brain(eb, test_input)

        if result.get('success', False):
            print("\nExecution successful!")
            print("Output:", result.get('output', 'No output'))
        else:
            print("\nExecution failed!")
            print("Error:", result.get('error', 'Unknown error'))

        return 0

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
