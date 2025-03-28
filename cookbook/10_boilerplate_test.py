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
from core.factory.orchestrator import Orchestrator

logger = get_logger(__name__)

def main():
    """Test the boilerplate tool through ElderBrain with proper initialization."""
    print("Boilerplate Tool with ElderBrain Example")
    print("---------------------------------------")
    print("This demonstrates using the boilerplate tool through")
    print("ElderBrain's three-phase processing approach.")
    print()

    try:
        # Initialize factory and orchestrator
        factory = AgentFactory.get_instance()
        factory.register_tool(get_tool())
        orchestrator = Orchestrator.get_instance(factory=factory)
        
        # Create ElderBrain instance
        eb = ElderBrain(orchestrator)
        
        # Test input
        test_input = "sample text for demonstration purposes"
        print(f"Testing boilerplate tool with input: {test_input}")

        # Process through ElderBrain's full three-phase approach
        info_results = eb.gather_information(f"Process this input: {test_input}")
        if 'error' in info_results:
            raise RuntimeError(f"Information gathering failed: {info_results['error']}")

        plan_results = eb.plan_solution(f"Plan how to process: {test_input}", info_results)
        if 'error' in plan_results:
            raise RuntimeError(f"Solution planning failed: {plan_results['error']}")

        execution_results = eb.execute_plan(f"Execute processing of: {test_input}", plan_results)
        
        # Print results
        print("\nExecution Results:")
        print("-" * 40)
        if 'error' in execution_results:
            print("Execution failed!")
            print(f"Error: {execution_results['error']}")
        else:
            print("Execution successful!")
            print("Final Result:", execution_results.get('execution_results', {}).get('final_result', 'No output'))
        
        return 0

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
