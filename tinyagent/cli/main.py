"""
Main CLI functionality for the tinyAgent framework.

This module provides the main entry point for the tinyAgent CLI, handling
command-line arguments, tool execution, and interactive mode.
"""

import os
import sys
import argparse
import re
from typing import List, Dict

from ..logging import get_logger, configure_logging
from ..config import load_config, get_config_value
from ..agent import Agent
from ..tool import Tool
from ..mcp import ensure_mcp_server

#import all of the tools 
from ..tools import *
from .colors import Colors
from .spinner import Spinner

# Set up logger
logger = get_logger(__name__)


def print_banner() -> None:
    """
    Print a banner for the CLI.
    
    This function prints a stylized ASCII art banner for the tinyAgent CLI,
    setting the visual tone for the application.
    """
    banner = rf"""
   __  .__                _____                         __   
_/  |_|__| ____ ___.__. /  _  \    ____   ____   _____/  |_ 
\   __\  |/    <   |  |/  /_\  \  / ___\_/ __ \ /    \   __\
 |  | |  |   |  \___  /    |    \/ /_/  >  ___/|   |  \  |  
 |__| |__|___|  / ____\____|__  /\___  / \___  >___|  /__|  
              \/\/            \//_____/      \/     \/      
 {Colors.BOLD}tinyAgent: AGI made simple{Colors.RESET}

 {Colors.BOLD}Made by (x) @tunahorse21 | A product of alchemiststudios.ai{Colors.RESET}
 
 {Colors.DARK_RED}IMPORTANT: tinyAgent is in EARLY BETA until V1. Use common sense.
 NOT RESPONSIBLE FOR ANY ISSUES that may arise from its use.{Colors.RESET}
"""
    
    print(banner)


def print_tools_box(tools: Dict[str, Tool]) -> None:
    """
    Print available tools in a simple, clean format.
    
    Args:
        tools: Dictionary of tool names to Tool objects
    """
    if not tools:
        return
    
    tool_names = list(tools.keys())
    if not tool_names:
        return

    # Calculate width
    width = 50
    
    print(f"\n{Colors.YELLOW}Available Tools:{Colors.RESET}")
    print(f"{Colors.DARK_RED}╭{'─' * width}╮{Colors.RESET}")
    
    # Simple header
    print(f"{Colors.DARK_RED}│ {Colors.YELLOW}#{Colors.RESET} │ {Colors.YELLOW}Tool{Colors.RESET} │ {Colors.YELLOW}Description{Colors.RESET}{' ' * 35} │{Colors.RESET}")
    
    # Divider
    print(f"{Colors.DARK_RED}├{'─' * width}┤{Colors.RESET}")
    
    # Print each tool with minimal formatting
    for i, name in enumerate(sorted(tool_names)):
        tool = tools[name]
        
        # Just truncate description without trying to format
        desc = tool.description
        if len(desc) > 65:
            desc = desc[:60] + "..."
        
        # Color for the tool name
        tool_color = Colors.LIGHT_RED if name == 'triage_agent' else Colors.CYAN
        
        # Extra simple format 
        print(f"{Colors.DARK_RED}│{Colors.RESET} {i+1} │ {tool_color}{name}{Colors.RESET} │ {desc}")
    
    print(f"{Colors.DARK_RED}╰{'─' * width}╯{Colors.RESET}")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the tinyAgent CLI.
    
    This function parses command-line arguments using argparse, providing a
    variety of options to control the behavior of the tinyAgent CLI.
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(description="TinyAgent - A simple LLM-powered agent framework")
    parser.add_argument("tool", nargs="?", help="Tool to execute directly or chain of tools separated by '|'")
    parser.add_argument("args", nargs="?", help="Tool arguments (e.g., file paths)")
    parser.add_argument("prompt", nargs="*", help="Prompt to pass to the tool or agent")
    parser.add_argument("--model", "-m", default=None, help="Model to use for LLM")
    parser.add_argument("--list-tools", "-l", action="store_true", help="List available tools")
    parser.add_argument("--output-dir", "-o", help="Directory to save output for tools that support it")
    parser.add_argument("--template", "-t", help="Path to prompt template file")
    parser.add_argument("--vars", "-v", help="Variables to use in the template as JSON string")
    parser.add_argument("--verbose", "-V", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress non-error output")
    parser.add_argument("--config", "-c", help="Path to configuration file")
    
    return parser.parse_args()


def load_tools() -> List[Tool]:
    """
    Load all available tools.
    
    This function loads tools from multiple sources, including built-in tools,
    tools in the tools directory, and MCP tools.
    
    Returns:
        List of Tool objects
    """
    try:
        # Load built-in tools that don't depend on MCP
        tools = [
            anon_coder_tool,
            llm_serializer_tool,
            ripgrep_tool,
            aider_tool,
            process_content,
            file_manipulator_tool,
            custom_text_browser_tool,
            final_answer_extractor,
        ]
        
        # Try to ensure MCP server is running, but don't fail if it doesn't start
        mcp_available = ensure_mcp_server()
        
        # Only add MCP-dependent tools if MCP server is available
        if mcp_available:
            tools.append(brave_web_search_tool)
            tools.append(duckduckgo_search_tool)
            logger.info("MCP server is available, MCP-dependent tools loaded")
        else:
            logger.warning("MCP server is not available, MCP-dependent tools will not be loaded")
        
        # Load external tools
        external_tools = load_external_tools()
        tools.extend(external_tools)
        
        return tools
    except ImportError as e:
        logger.error(f"Error loading tools: {e}")
        return []


def format_result(result):
    """
    Format results for CLI display with special handling for different result types.
    
    Args:
        result: The result to format
        
    Returns:
        Formatted string representation of the result
    """
    if not result:
        return "No results available"
    
    # Handle list of search results with title/description/url structure
    if isinstance(result, list) and result and all(isinstance(item, dict) and 'title' in item for item in result):
        output = ["📊 Search Results:", ""]
        for idx, item in enumerate(result, 1):
            title = item.get('title', 'No title')
            description = item.get('description', 'No description')
            url = item.get('url', 'No URL')
            
            # Clean up HTML tags if present
            description = re.sub(r'<[^>]+>', '', description)
            
            output.extend([
                f"{Colors.BOLD}{idx}. {Colors.YELLOW}{title}{Colors.RESET}",
                f"   {Colors.OFF_WHITE}{description}{Colors.RESET}",
                f"   {Colors.BLUE}🔗 {url}{Colors.RESET}",
                ""
            ])
        return "\n".join(output)
    
    # Handle dictionaries
    elif isinstance(result, dict):
        output = []
        for key, value in result.items():
            if isinstance(value, (list, dict)):
                output.append(f"{Colors.BOLD}{key}:{Colors.RESET}")
                output.append(format_result(value))
            else:
                output.append(f"{Colors.BOLD}{key}:{Colors.RESET} {value}")
        return "\n".join(output)
    
    # Handle generic lists
    elif isinstance(result, list):
        return "\n".join([f"{Colors.CYAN}•{Colors.RESET} {format_result(item)}" for item in result])
    
    # Default for other types
    else:
        return str(result)


def main() -> None:
    """
    Main entry point for the tinyAgent CLI.
    
    This function handles command-line arguments, initializes the agent,
    and runs tools or enters interactive mode as appropriate.
    """
    args = parse_arguments()
    
    # Configure logging based on verbosity
    log_level = "DEBUG" if args.verbose else "INFO"
    if args.quiet:
        log_level = "ERROR"
    
    # Load configuration
    config = load_config(args.config)
    
    # Configure logging
    configure_logging(log_level, config)
    
    # Load tools
    tools = load_tools()
    
    # Create a dictionary of tools by name
    tools_dict = {tool.name: tool for tool in tools if hasattr(tool, 'name')}
    
    # Handle --list-tools
    if args.list_tools:
        print("Available tools:")
        for tool in tools:
            if hasattr(tool, 'name') and hasattr(tool, 'description'):
                print(f"  {tool.name}: {tool.description}")
        return
    
    # Parse variables for template if provided
    template_vars = None
    if args.vars:
        try:
            import json
            template_vars = json.loads(args.vars)
            logger.debug(f"Template variables: {template_vars}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing template variables: {e}")
            print(f"{Colors.error('Invalid JSON format for template variables')}")

    # Handle case where we have a prompt and template but no tool (direct agent execution)
    if not args.tool and args.prompt and args.template:
        logger.info(f"Executing agent directly with template: {args.template}")
        
        # Get the singleton factory instance
        from ..factory.agent_factory import AgentFactory
        factory = AgentFactory.get_instance()
        
        # Load and register tools
        for tool in tools:
            if hasattr(tool, 'name'):
                factory.register_tool(tool)
        
        # Create an agent without factory
        agent = Agent(model=args.model)
        
        # Register all tools directly with the agent
        for tool in tools:
            if hasattr(tool, 'name') and tool.name != "chat":  # Skip chat tool since agent already adds it
                agent.create_tool(
                    name=tool.name,
                    description=tool.description,
                    func=tool.func,
                    parameters=tool.parameters
                )
        
        # Process prompt
        user_query = ' '.join(args.prompt)
        
        try:
            with Spinner(f"Processing with template {args.template}..."):
                result = agent.run(user_query, template_path=args.template, variables=template_vars)
            
            print(f"\n{Colors.OFF_WHITE}Query processed with template{Colors.RESET}")
            print(f"{Colors.LIGHT_RED}╭─{Colors.RESET}")
            print(f"{Colors.OFF_WHITE}{result}{Colors.RESET}")
            print(f"{Colors.LIGHT_RED}╰─{Colors.RESET}")
            
        except Exception as e:
            logger.error(f"Error processing with template: {str(e)}")
            print(f"{Colors.error(f'Error processing with template: {str(e)}')}")
        
        return
    
    # Print banner and tools box if no specific command
    if not args.tool and not args.prompt:
        print_banner()
        
        # Add triage_agent for display purposes
        if 'triage_agent' not in tools_dict:
            tools_dict['triage_agent'] = Tool(
                name="triage_agent",
                description="Triages incoming queries, calls internal agents & agentfactory",
                parameters={"message": "string", "allow_new_tools": "any"},
                func=lambda message, allow_new_tools=False: message
            )
            
        print_tools_box(tools_dict)
        
        print(f"""
{Colors.OFF_WHITE}+-----------+ --> +---------------+ --> +--------------+ --> +------------------+ --> +-----------+
| Triage    |     | AgentFactory  |     | Specialized  |     | Infinite         |     | Structured|
| Agent     |     | (Creates      |     | Agents       |     | Handoff          |     | Output    |
|           |     | Agents on the |     | (dynamically |     |                  |     |           |
+-----------+     | fly via NLP)  |     | created)     |     +------------------+     +-----------+
                   +---------------+     +--------------+                  |
                   |_______________________________________________________|{Colors.RESET}
""")
        print(f"\n{Colors.OFF_WHITE}Enter in a task and tinyAgent will execute based on tools{Colors.RESET}")
        print(f"\n{Colors.OFF_WHITE}Tool chaining supported with '|' (e.g. 'file_hunter | pm'){Colors.RESET}")
        print(f"{Colors.OFF_WHITE}Special commands:{Colors.RESET}")
        print(f"{Colors.OFF_WHITE}  /chat - Enter direct chat mode with the LLM{Colors.RESET}")
        print(f"{Colors.OFF_WHITE}Type 'exit' or 'quit' to exit{Colors.RESET}")
        
        # Interactive mode
        run_interactive_mode(args, tools_dict)
    else:
        # Direct tool execution
        logger.info("Executing tool directly")
        
        # Get the tool to execute
        tool_name = args.tool
        
        # Check if it's a chain of tools
        if '|' in tool_name:
            logger.info(f"Tool chain detected: {tool_name}")
            # Handle tool chaining (execute tools in sequence)
            tool_names = [t.strip() for t in tool_name.split('|')]
            
            # Create a chain of tools
            tools_to_execute = []
            for name in tool_names:
                if name in tools_dict:
                    tools_to_execute.append(tools_dict[name])
                else:
                    logger.error(f"Tool not found: {name}")
                    print(f"Tool not found: {name}")
                    return
            
            # Execute the tool chain
            result = None
            for tool in tools_to_execute:
                try:
                    # Parse arguments for this tool
                    # For simplicity, we're using the same args for all tools in the chain
                    # In a real implementation, you'd want to parse arguments per tool
                    tool_args = {}
                    if args.args:
                        tool_args = {list(tool.parameters.keys())[0]: args.args}
                    
                    # If we have a result from previous tool, use it as input
                    if result is not None:
                        # Use the first parameter
                        first_param = list(tool.parameters.keys())[0]
                        tool_args[first_param] = result
                    
                    # Add prompt if provided
                    if args.prompt and not tool_args:
                        # Use the prompt as the first parameter
                        first_param = list(tool.parameters.keys())[0]
                        tool_args[first_param] = ' '.join(args.prompt)
                    
                    logger.info(f"Executing tool: {tool.name} with args: {tool_args}")
                    result = tool(**tool_args)
                    
                except Exception as e:
                    logger.error(f"Error executing tool {tool.name}: {str(e)}")
                    print(f"Error executing tool {tool.name}: {str(e)}")
                    return
            
            # Print the final result
            print(result)
            
        else:
            # Single tool execution
            if tool_name not in tools_dict:
                logger.error(f"Tool not found: {tool_name}")
                print(f"Tool not found: {tool_name}")
                return
            
            tool = tools_dict[tool_name]
            
            try:
                # Parse arguments
                tool_args = {}
                
                # Get the first parameter for text input
                first_param = list(tool.parameters.keys())[0]
                if args.args:
                    tool_args[first_param] = args.args
                elif args.prompt:
                    tool_args[first_param] = ' '.join(args.prompt)
                
                # Add default values for other parameters from manifest
                if hasattr(tool, 'manifest'):
                    for param_name, param_info in tool.manifest.get('parameters', {}).items():
                        if isinstance(param_info, dict) and not param_info.get('required', True):
                            if param_name not in tool_args and 'default' in param_info:
                                tool_args[param_name] = param_info['default']
                
                logger.info(f"Executing tool: {tool.name} with args: {tool_args}")
                result = tool(**tool_args)
                print(result)
                
            except Exception as e:
                logger.error(f"Error executing tool {tool.name}: {str(e)}")
                print(f"Error executing tool {tool.name}: {str(e)}")


def run_interactive_mode(args: argparse.Namespace, tools_dict: Dict[str, Tool]) -> None:
    """
    Run the interactive mode of the CLI.
    
    Args:
        args: Parsed command-line arguments
        tools_dict: Dictionary of tool names to Tool objects
    """
    # Ensure environment variables are loaded
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file from the current directory
    
    model = args.model
    
    # Get the singleton factory instance
    from ..factory.agent_factory import AgentFactory
    factory = AgentFactory.get_instance()
    
    # Register all tools with the factory
    for tool_name, tool in tools_dict.items():
        # Check if tool is already registered (since has_tool method isn't available)
        if tool_name not in factory._tools:
            factory.register_tool(tool)
    
    # Create an agent without the factory
    agent = Agent(model=model)
    
    # Register all tools directly with the agent
    for tool_name, tool in tools_dict.items():
        if tool_name not in ["chat"]:  # Skip chat tool since agent already adds it
            agent.create_tool(
                name=tool.name,
                description=tool.description,
                func=tool.func,
                parameters=tool.parameters
            )
    
    # Parse variables for template if provided
    template_vars = None
    if args.vars:
        try:
            import json
            template_vars = json.loads(args.vars)
            logger.debug(f"Template variables: {template_vars}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing template variables: {e}")
            print(f"{Colors.error('Invalid JSON format for template variables')}")
    
    while True:
        try:
            user_input = input(f"\n{Colors.LIGHT_RED}❯{Colors.OFF_WHITE} ")
            if user_input.lower() in ["exit", "quit"]:
                print(f"\n{Colors.LIGHT_RED}Goodbye!{Colors.RESET}")
                break
            elif user_input.lower() == "/chat":
                # Enter chat mode
                from ..chat import run_chat_mode
                print(f"\n{Colors.OFF_WHITE}Entering chat mode with {model or 'default model'}{Colors.RESET}")
                run_chat_mode(model=model)
                continue

            # Check if this is a tool chain
            if "|" in user_input:
                tools_chain = [t.strip() for t in user_input.split("|")]
                result = None
                try:
                    for tool_cmd in tools_chain:
                        # Parse tool command
                        parts = tool_cmd.split(maxsplit=2)  # Split into max 3 parts for multi-param tools
                        tool_name = parts[0]
                        
                        if tool_name not in tools_dict:
                            raise ValueError(f"Tool not found: {tool_name}")
                        
                        tool = tools_dict[tool_name]
                        
                        # Handle tool-specific parameter requirements
                        tool_args = {}
                        if tool_name == "aider":
                            # Special handling for aider in chain
                            if len(parts) < 2:
                                raise ValueError("Missing required parameter: files")
                            if len(parts) < 3 and result is None:
                                raise ValueError("Missing required parameter: prompt")
                            tool_args["files"] = parts[1]
                            tool_args["prompt"] = parts[2] if len(parts) > 2 else result
                        else:
                            # Default handling for single-parameter tools
                            first_param = list(tool.parameters.keys())[0]
                            if len(parts) > 1:
                                tool_args[first_param] = parts[1]
                            elif result is not None:
                                tool_args[first_param] = result
                            
                        logger.info(f"Executing tool in chain: {tool_name} with args: {tool_args}")
                        result = tool(**tool_args)
                        
                    # Print final result
                    print(f"\n{Colors.OFF_WHITE}Chain execution completed{Colors.RESET}")
                    print(f"{Colors.LIGHT_RED}╭─{Colors.RESET}")
                    print(f"{Colors.OFF_WHITE}{result}{Colors.RESET}")
                    print(f"{Colors.LIGHT_RED}╰─{Colors.RESET}")
                    
                except Exception as e:
                    print(f"\n{Colors.DARK_RED}Chain execution failed: {str(e)}{Colors.RESET}")
                continue

            # Check if this is a direct tool call
            first_word = user_input.split()[0]
            if first_word in tools_dict:
                try:
                    # Parse tool command
                    import shlex
                    parts = shlex.split(user_input)
                    tool_name = parts[0]
                    tool = tools_dict[tool_name]

                    # Handle tool-specific parameter requirements
                    tool_args = {}
                    if tool_name == "aider":
                        # Special handling for aider's two parameters
                        if len(parts) < 2:
                            raise ValueError("Missing required parameter: files")
                        if len(parts) < 3:
                            raise ValueError("Missing required parameter: prompt")
                        tool_args = {
                            "files": parts[1],
                            "prompt": parts[2]
                        }
                    elif tool_name == "brave_web_search":
                        # Ensure MCP server is running
                        from tinyagent.mcp import ensure_mcp_server
                        ensure_mcp_server()
                        
                        # Special handling for brave_web_search parameters
                        if len(parts) < 2:
                            raise ValueError("Missing required parameter: query")
                        tool_args = {"query": parts[1]}
                        if len(parts) >= 3:
                            try:
                                tool_args["count"] = int(parts[2])
                            except ValueError:
                                raise ValueError("Count parameter must be a number")
                    else:
                        # Default handling for single-parameter tools
                        first_param = list(tool.parameters.keys())[0]
                        if len(parts) > 1:
                            tool_args[first_param] = parts[1]
                    
                    logger.info(f"Executing tool directly: {tool_name} with args: {tool_args}")
                    result = tool(**tool_args)
                    
                    # Print result
                    print(f"\n{Colors.OFF_WHITE}Tool execution completed{Colors.RESET}")
                    print(f"{Colors.LIGHT_RED}╭─{Colors.RESET}")
                    print(f"{Colors.OFF_WHITE}{result}{Colors.RESET}")
                    print(f"{Colors.LIGHT_RED}╰─{Colors.RESET}")
                    
                except Exception as e:
                    print(f"\n{Colors.DARK_RED}Tool execution failed: {str(e)}{Colors.RESET}")
                continue
            
            # Process the user input with agent using template if provided
            if args.template:
                with Spinner(f"Processing with template {args.template}..."):
                    try:
                        result = agent.run(user_input, template_path=args.template, variables=template_vars)
                        print(f"\n{Colors.OFF_WHITE}Query processed with template{Colors.RESET}")
                        print(f"{Colors.LIGHT_RED}╭─{Colors.RESET}")
                        print(f"{Colors.OFF_WHITE}{result}{Colors.RESET}")
                        print(f"{Colors.LIGHT_RED}╰─{Colors.RESET}")
                    except Exception as e:
                        print(f"\n{Colors.DARK_RED}Template processing failed: {str(e)}{Colors.RESET}")
                continue
            
            # Fallback to triage agent for other inputs
            from ..factory.orchestrator import Orchestrator
            
            with Spinner("Processing with Triage Agent..."):
                orchestrator = Orchestrator.get_instance()
                task_id = orchestrator.submit_task(user_input, need_permission=False)
                status = orchestrator.get_task_status(task_id)
                
            if status.status == "completed":
                print(f"\n{Colors.OFF_WHITE}Task completed by Triage Agent{Colors.RESET}")
                print(f"{Colors.OFF_WHITE}Result:{Colors.RESET}")
                print(f"{Colors.LIGHT_RED}╭─{Colors.RESET}")
                try:
                    # Try to parse json if possible
                    import json
                    if isinstance(status.result, str):
                        try:
                            parsed_result = json.loads(status.result)
                            formatted = format_result(parsed_result)
                            print(f"{formatted}")
                        except json.JSONDecodeError:
                            # Not JSON, print as is
                            print(f"{Colors.OFF_WHITE}{status.result}{Colors.RESET}")
                    else:
                        # Already a Python object
                        formatted = format_result(status.result)
                        print(f"{formatted}")
                except Exception:
                    # Fallback to plain output
                    print(f"{Colors.OFF_WHITE}{status.result}{Colors.RESET}")
                print(f"{Colors.LIGHT_RED}╰─{Colors.RESET}")
            else:
                print(f"\n{Colors.DARK_RED}Task failed: {status.error}{Colors.RESET}")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            print(f"{Colors.error(str(e))}")


if __name__ == "__main__":
    main()

""" Summary of the Issue:
The core problem was that you couldn't reliably run the duckduckgo_search tool directly from the interactive CLI using commands like ❯ duckduckgo_search "query" --max_results 5. This manifested in two main ways:
Fallback to Triage Agent: Initially, the command wasn't recognized as a direct tool call at all. It was passed to the Triage Agent, which also failed because it either didn't know about duckduckgo_search or misinterpreted the command. This was likely due to the tool not being loaded correctly in the interactive context (potentially related to the MCP check).
Missing Parameter Error: After fixing the tool loading, the CLI did recognize duckduckgo_search for direct execution. However, it then failed with a Missing required parameter: max_results error. This happened because the argument parsing logic in the CLI for direct calls was too basic – it only grabbed the first argument (keywords) and ignored named arguments like --max_results. A validation step then failed because max_results was expected (based on the tool's definition) but wasn't provided by the faulty parser.
What We Learned:
CLI Parsing is Crucial: The way the interactive CLI (main.py) parses commands is critical for determining whether a tool is run directly or handed off to an agent. Simple parsing can easily break with prefixes (❯) or standard argument formats (--option value).
Conditional Tool Loading Matters: Tools might only be loaded if certain conditions are met (like the MCP server running). If a tool isn't loaded, it can't be called directly by name.
Framework Validation Exists: There's a validation step before a tool's specific function code runs. This validation checks the arguments provided by the caller against the parameters defined in the tool's Tool object.
Defaults Don't Always Save You: Even if a tool's function code defines default values for parameters (like duckduckgo_search does for max_results), an error can occur before that code runs if the framework's validation layer strictly requires the parameter based on its definition.
Hardcoded Logic is Brittle: The interactive CLI had specific, hardcoded argument handling for aider and brave_web_search, but a very basic default for everything else. This made it inflexible for tools with multiple or named arguments.
Debugging Requires Tracing: We had to follow the command from input, through parsing in main.py, tool loading checks, the direct execution attempt, the argument validation step, and the Triage Agent fallback path to understand the different failure points. """