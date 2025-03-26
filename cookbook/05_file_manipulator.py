#!/usr/bin/env python3
"""
Example 5: File Manipulation Tool

This example demonstrates how to use the built-in file manipulation tool
that provides safe CRUD operations on files within a configured directory.

Important notes:
1. Paths are relative to the current working directory by default
2. The directory structure will be created if it doesn't exist
3. Use proper path formatting with directories (e.g., 'tinyAgent_output/test.txt')
4. Configure allowed extensions and other safety features in config.yml
"""

import os
import sys

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import Agent
from core.factory.agent_factory import AgentFactory
from core.tools import file_manipulator_tool


def main():
    """Create and run an agent with file manipulation capabilities."""
    print("File Manipulator Example")
    print("-----------------------")
    print("This example demonstrates using the file manipulator tool to perform")
    print("CRUD operations on files. Files are created relative to the current")
    print("working directory unless configured otherwise.")
    print()
    
    # Get the singleton factory instance
    factory = AgentFactory.get_instance()
    
    # Register the built-in file manipulation tool
    factory.register_tool(file_manipulator_tool)
    
    # Create an agent that will use the factory
    agent = Agent(factory=factory)
    
    # Example operations
    operations = [
        # Create a text file
        "Create a file named 'tinyAgent_output/test.txt' with content 'Hello, World!'",
        
        # Read the file
        "Read the contents of 'tinyAgent_output/test.txt'",
        
        # Update the file
        "Update 'tinyAgent_output/test.txt' with content 'Hello, tinyAgent!'",
        
        # List directory
        "List all files in the 'tinyAgent_output' directory",
        
        # Delete the file
        "Delete the file 'tinyAgent_output/test.txt'",
        
        # Final directory listing
        "List all files in the 'tinyAgent_output' directory"
    ]
    
    # Run each operation
    for query in operations:
        print(f"\nRunning query: '{query}'")
        try:
            result = agent.run(query)
            if isinstance(result, dict):
                if result.get("status") == "error":
                    print(f"Operation failed: {result.get('error')}")
                    print(f"Details: {result}")
                else:
                    print(f"Result: {result}")
                    # Add more context for directory listings
                    if "items" in result:
                        if not result["items"]:
                            print("Directory is empty")
                        else:
                            print("\nDirectory contents:")
                            for item in result["items"]:
                                print(f"- {item['name']} ({item['type']})")
                                if item['type'] == 'file':
                                    print(f"  Size: {item['size']} bytes")
                                    print(f"  Permissions: {item['permissions']}")
            else:
                print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print("Traceback:")
            traceback.print_exc()


if __name__ == "__main__":
    main() 