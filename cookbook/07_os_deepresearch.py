#!/usr/bin/env python3
"""
Example 6: Enhanced Deep Research Agent

This example demonstrates how to use the enhanced deep research agent
to perform comprehensive research tasks using a three-phase approach:
1. Information Gathering - Collects data from multiple sources
2. Analysis & Planning - Processes information and plans next steps
3. Synthesis & Reporting - Creates comprehensive research reports

The tool uses web search, web page navigation, content extraction,
and text processing to provide detailed answers to complex queries.
"""

import os
import sys
import json

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tinyagent.tools.enhanced_deepsearch import enhanced_deepsearch_tool


def main():
    """Create and run an agent with enhanced deep research capabilities."""
    print("Enhanced Deep Research Example")
    print("-----------------------------")
    print("This example demonstrates using the enhanced deepsearch tool")
    print("to perform comprehensive research on a topic, synthesize information,")
    print("and generate structured reports on findings.")
    print("Note: This process may take several minutes to complete.")
    print()

    # Define a simple research query
    research_query = "TASK: Explain the latest agentic system applications in the real world and the latest research in the field"
    print(f"Starting research on: '{research_query}'")
    print("Processing request (this may take a few minutes)...")
    print()
    
    # Perform the research
    try:
        results = enhanced_deepsearch_tool.process_query(research_query)
        
        # Check for success
        if results.get("success", False):
            print("\nResearch completed successfully!")
            print("----------------------------------")
            
            # Print summary statistics
            print("\nResearch Statistics:")
            phases = results.get("phases", {})
            print(f"- Gathered information from {phases.get('gathering', {}).get('sources', 0)} sources")
            print(f"- Analyzed {phases.get('analysis', {}).get('insights', 0)} insights")
            print(f"- Completed in {sum(p.get('steps', 0) for p in phases.values())} total steps")
            
            # Print the summary
            summary = results.get("summary")
            if summary:
                print("\nSummary of Findings:")
                print("-------------------")
                print(summary)
            
            # Report information
            report = results.get("report")
            if report:
                print("\nReport Sections:")
                print("--------------")
                for section in report.get("sections", []):
                    print(f"- {section.get('heading', 'Unnamed Section')}")
            
            # Print location of saved report if available
            if phases.get("synthesis", {}).get("steps", 0) > 2:
                print("\nA detailed report has been saved to the tinyAgent_output/research directory.")
        else:
            print("\nResearch could not be completed successfully.")
            print(f"Error: {results.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"Error during research: {str(e)}")
        import traceback
        print("Traceback:")
        traceback.print_exc()


if __name__ == "__main__":
    main()
