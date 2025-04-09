#!/usr/bin/env python3
"""
Example 10: Full Elder Brain Pipeline Demo

This example shows how to use the ElderBrain meta-agent to handle a complex task
from a single prompt, running all three phases:

1. Information Gathering
2. Solution Planning
3. Execution

The Elder Brain will analyze the task, design a plan, execute the plan with real tools,
and return the final result.
"""

import os
import sys
import json

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tinyagent.factory.orchestrator import Orchestrator
from tinyagent.factory.elder_brain import ElderBrain

def main():
    # Initialize orchestrator
    orchestrator = Orchestrator.get_instance()

    # Create ElderBrain
    elder_brain = ElderBrain(orchestrator)

    # Define a complex task prompt
    task_description = "Research the latest AI trends and generate a detailed report with code examples."

    print("\n===== ELDER BRAIN FULL PIPELINE DEMO =====")
    print(f"Task: {task_description}\n")

    # Phase 1: Information Gathering
    info_results = elder_brain.gather_information(task_description)
    print("\n--- Phase 1: Information Gathering ---")
    print(json.dumps(info_results, indent=2))

    # Phase 2: Solution Planning
    plan_results = elder_brain.plan_solution(task_description, info_results)
    print("\n--- Phase 2: Solution Planning ---")
    print(json.dumps(plan_results, indent=2))

    # Extract the plan dict
    plan = plan_results.get("plan", {})

    # Phase 3: Execution
    execution_results = elder_brain.execute_plan(task_description, plan)
    print("\n--- Phase 3: Execution ---")
    print(json.dumps(execution_results, indent=2))

    print("\n===== ELDER BRAIN DEMO COMPLETE =====")

if __name__ == "__main__":
    main()