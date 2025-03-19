#!/usr/bin/env python3
"""
Example 5: ElderBrain Report Generation

This example demonstrates ElderBrain's ability to generate comprehensive reports
by directly processing a complex task through its three-phase approach:

1. Information Gathering: Collect relevant data
2. Solution Planning: Analyze information and create a structured plan
3. Execution: Generate a detailed report with actual content

Unlike previous examples, this focuses on ElderBrain's content generation capabilities,
showing how it can create substantive reports that include actual findings and analysis.
"""

import os
import sys
import json
import time
from typing import Dict, Any

# Add parent directory to the path so we can import the core package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory.orchestrator import Orchestrator, TaskStatus
from core.factory.agent_factory import AgentFactory
from core.tools.brave_search import brave_web_search_tool
from core.decorators import tool
from core.logging import configure_logging, get_logger

# Configure logging to see ElderBrain's output
configure_logging(log_level="INFO")
logger = get_logger(__name__)


def main():
    """
    Demonstrate ElderBrain's ability to generate comprehensive reports.
    
    This function:
    1. Sets up the necessary infrastructure (Orchestrator, AgentFactory)
    2. Registers tools for content generation
    3. Creates a task that specifically requests report content
    4. Processes the task through ElderBrain's three phases
    5. Displays the comprehensive report output
    """
    print_header()
    
    # Setup orchestrator and factory
    orchestrator = Orchestrator.get_instance()
    factory = AgentFactory.get_instance()
    
    # Configure rate limits for brave search
    if not hasattr(factory, 'config'):
        factory.config = {}
    if 'rate_limits' not in factory.config:
        factory.config['rate_limits'] = {
            'global': 5,  # Default global limit
            'tools': {
                'brave_web_search': 1  # Limit Brave to 1 call per minute
            }
        }
    
    # Register necessary tools
    factory.register_tool(brave_web_search_tool)
    register_content_generation_tool(factory)
    
    # Define a research topic
    research_topic = "The impact of artificial intelligence on healthcare"
    print(f"Research Topic: {research_topic}\n")
    
    # Create a detailed task that explicitly requests content
    task = TaskStatus(
        task_id="elderbrain_content_generation",
        description=(
            f"Research '{research_topic}' and create a comprehensive report with substantive content. "
            f"The report should include an executive summary, key findings, analysis, and recommendations. "
            f"Include specific examples, data points, and insights throughout the report."
            f"You must save the report to a file in the directory, this report must be college level."
        )
    )
    
    print("Starting ElderBrain report generation process...")
    print("ElderBrain will process this task in three distinct phases and generate content.\n")
    
    # Process the task through ElderBrain
    result = orchestrator.elder_brain.process_phased_task(task)
    
    # Display and save the results
    extract_and_display_report(result)


def print_header():
    """Print a header explaining this example's purpose."""
    print("="*80)
    print("ELDERBRAIN CONTENT GENERATION EXAMPLE")
    print("="*80)
    print("\nDemonstrating ElderBrain's ability to generate comprehensive reports:\n")
    print("┌────────────────────────┐      ┌────────────────────────┐      ┌────────────────────────┐")
    print("│ PHASE 1                │      │ PHASE 2                │      │ PHASE 3                │")
    print("│ Information Gathering  │ ──▶  │ Solution Planning      │ ──▶  │ Content Generation     │")
    print("│                        │      │                        │      │                        │")
    print("│ • Research sources     │      │ • Structure outline    │      │ • Write detailed report│")
    print("│ • Collect key data     │      │ • Identify key points  │      │ • Include examples     │")
    print("│ • Identify trends      │      │ • Organize sections    │      │ • Format findings      │")
    print("└────────────────────────┘      └────────────────────────┘      └────────────────────────┘")
    print("\nThis example demonstrates ElderBrain generating substantive report content.\n")


def register_content_generation_tool(factory):
    """
    Register a tool specifically for generating comprehensive report content.
    
    This tool is designed to create detailed reports with substantive content,
    analysis, and insights - not just metadata about the report structure.
    
    Args:
        factory: The AgentFactory to register the tool with
    """
    @tool
    def generate_report_content(topic: str, outline: str = None) -> str:
        """
        CREATE A COMPREHENSIVE RESEARCH REPORT WITH ACTUAL CONTENT.
        
        You must generate a complete, detailed report with substantive information,
        not just a description or summary of what a report would contain.
        
        The report MUST include:
        - A title and executive summary
        - Multiple sections with actual content (not placeholders)
        - Specific examples, data points, and real-world applications
        - Analysis of benefits, challenges, and implications
        - Concrete recommendations based on the research
        - A conclusion that synthesizes the key findings
        
        Format the report with proper Markdown headings, bullet points, and emphasis
        where appropriate. Make it professional, informative, and comprehensive.
        
        Args:
            topic: The research topic for the report
            outline: Optional outline or structure for the report
            
        Returns:
            The complete research report with comprehensive content
        """
        print(f"Generating a comprehensive, content-rich report on: {topic}")
        
        # Import the LLM to actually generate content
        from ...agent import get_llm
        llm = get_llm()
        
        # Prepare a prompt for the LLM to generate the report
        prompt = f"""
        Create a comprehensive, college-level report on the topic: {topic}
        
        Use this research information if provided:
        {outline if outline else "No specific research provided"}
        
        The report MUST include:
        - A title and executive summary
        - Multiple sections with actual content (not placeholders)
        - Specific examples, data points, and real-world applications 
        - Analysis of benefits, challenges, and implications
        - Concrete recommendations based on the research
        - A conclusion that synthesizes the key findings
        
        Format the report with proper Markdown headings, bullet points, and emphasis.
        Make it professional, informative, and comprehensive.
        """
        
        # Actually generate the report content
        report = llm(prompt)
        return report
    
    # Register the tool with the factory
    factory.register_tool(generate_report_content._tool)
    print("Registered content generation tool for creating comprehensive reports")


def extract_and_display_report(result: Dict[str, Any]):
    """
    Extract and display the actual report content from ElderBrain's results.
    
    This function focuses on finding and displaying the substantive report content
    that ElderBrain has generated, while also saving the full result structure.
    
    Args:
        result: The raw result from ElderBrain processing
    """
    # Save the full result to a file for reference
    save_to_file(result, "elderbrain_full_result.json")
    
    print("\n" + "="*80)
    print("ELDERBRAIN REPORT GENERATION RESULTS")
    print("="*80)
    
    # Check for successful processing
    if not result.get("success", False):
        print(f"\nElderBrain processing failed: {result.get('error', 'Unknown error')}")
        return
    
    # Print phase summary
    phases = result.get("phases", {})
    print("\nPhases completed by ElderBrain:")
    for phase_name in phases:
        print(f"- {phase_name}")
    
    # Extract and display the actual report content
    print("\n" + "="*80)
    print("COMPREHENSIVE REPORT")
    print("="*80 + "\n")
    
    # Try to find the report content in different possible locations
    report_content = None
    
    # Check for recovery mode report
    recovery_mode = False
    if "execution" in phases:
        execution = phases["execution"]
        if "execution_results" in execution:
            exec_results = execution["execution_results"]
            if exec_results.get("recovery_mode") == "llm_knowledge":
                recovery_mode = True
                print("⚠️ Note: This report was generated using LLM knowledge due to tool execution issues.\n")
    
    # Check execution phase for the report content
    if "execution" in phases:
        execution = phases["execution"]
        
        # Look for content in execution_results.final_result
        if "execution_results" in execution:
            exec_results = execution["execution_results"]
            if "final_result" in exec_results and isinstance(exec_results["final_result"], str) and len(exec_results["final_result"]) > 100:
                report_content = exec_results["final_result"]
                
                # Print execution issues if any
                if exec_results.get("encountered_issues"):
                    print("Issues encountered during execution:")
                    for issue in exec_results["encountered_issues"][:3]:  # Show first 3 issues
                        print(f"- {issue}")
                    print()
    
    # If not found in execution phase, check the top-level final_result
    if not report_content and "final_result" in result and isinstance(result["final_result"], str) and len(result["final_result"]) > 100:
        report_content = result["final_result"]
    
    # If found, display the report content
    if report_content:
        print(report_content)
        
        # Also save the report content to a separate file
        save_to_file({"report": report_content}, "elderbrain_report.json")
        print("\nReport content saved to: elderbrain_report.json")
    else:
        # If we couldn't find substantive content, display the raw results
        # and provide info about what we expected
        print("Could not extract a comprehensive report with substantive content.")
        print("ElderBrain provided a task execution summary instead of detailed report content.")
        print("\nRaw execution results:")
        
        if "execution" in phases and "execution_results" in phases["execution"]:
            print(json.dumps(phases["execution"]["execution_results"], indent=2, default=str))
        else:
            print("No execution results available.")
        
        print("\nPlease check elderbrain_full_result.json for complete details.")


def save_to_file(data, filename):
    """
    Save data to a file in the current directory.
    
    Args:
        data: The data to save
        filename: The name of the file to save to
    """
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"\nError saving to file {filename}: {str(e)}")


if __name__ == "__main__":
    main()
