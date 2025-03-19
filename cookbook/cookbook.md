
# tinyAgent Cookbook

This directory contains examples demonstrating different ways to create and use agents within the tinyAgent framework.

## Overview

1. `01_basic_agent.py` - Simple agent creation with direct tool definition
2. `02_factory_agent.py` - Using AgentFactory for centralized tool management
3. `03_decorator_agent.py` - Simplified agent creation using decorators
4. `04_dynamic_agent.py` - Dynamic agent creation based on task requirements
5. `05_mcp_orchestration.py` - Complex orchestration with MCP integration
6. `05_elder_brain_mcp_orchestration.py` - ElderBrain architecture with direct control
7. `05_elder_brain_report_generation.py` - ElderBrain content generation capabilities

## Running the Examples

Make sure you have set up your environment variables correctly before running these examples. At minimum, you'll need:

```
OPENROUTER_API_KEY=your_api_key_here
```

For examples using MCP (Model Context Protocol) like `05_mcp_orchestration.py`, you may also want to set:

```
BRAVE=your_brave_api_key_here
```

### Running an Example

```bash
cd /path/to/tinyagentV0.3
python examples/01_basic_agent.py
```

## Example Details

### 1. Basic Agent

The simplest way to create a TinyAgent with a custom tool using the factory pattern. Shows:
- Tool creation through AgentFactory
- Agent initialization with factory
- Running a query

**Important Note**: As of the latest update, all Agent instances must be created with a factory reference. The older pattern of directly passing tools to the Agent constructor is no longer supported.

### 2. Factory Agent

Demonstrates using the AgentFactory for improved tool management. Features:
- Centralized tool registration
- Rate limiting capabilities
- Tool usage statistics

### 3. Decorator Agent

Shows a more concise way to define tools using decorators. Highlights:
- Type hint integration for automatic parameter mapping
- Simplified tool creation syntax
- Optional parameters

### 4. Dynamic Agent

Showcases dynamic agent creation based on natural language requirements. Demonstrates:
- Task analysis to determine required tools
- Automatic tool selection
- Dynamic agent specialization

### 6. Direct ElderBrain MCP Orchestration

A first principles implementation of ElderBrain architecture that bypasses the standard triage mechanism. Features:
- Direct usage of ElderBrain's three-phase approach:
  1. Information Gathering: Collecting relevant data via web search
  2. Solution Planning: Analyzing information and creating a structured plan
  3. Execution: Generating a comprehensive research report
- Phase-aligned tools that specifically match each ElderBrain phase
- Detailed visualization of results from each phase
- Clear demonstration of information flow between phases
- Educational display of the ElderBrain architecture and its benefits

### 7. ElderBrain Report Generation

An advanced example focused on ElderBrain's content generation capabilities. Features:
- Tool specifically designed for comprehensive report generation
- Explicit instructions to produce substantive content
- Extraction and display of the actual report content
- Enhanced task description to guide content creation
- Separation between metadata tracking and actual content generation
- Multiple approaches to locate and extract the report content
- Saving both the full result structure and the focused report content

## Working with External Tools

tinyAgent supports external tools implemented in other languages via a JSON-based communication protocol. External tools are loaded from the `external_tools` directory, where each tool has its own subdirectory containing:

- A `manifest.json` file defining the tool's name, description, parameters, and executable
- The executable file itself (can be in any language - C, Go, Rust, Bash, etc.)

Example external tools:
- `text_rank` - Text compression using the TextRank algorithm (implemented in C)

External tools are automatically loaded when tinyAgent starts and can be used like any other tool through:
- Direct execution via the CLI: `python main.py text_rank "text to compress"`
- Within Agent instances via the factory

## Best Practices

- Use the simplest approach that meets your needs (Basic or Decorator for simple agents)
- **Always** create Agent instances using a factory rather than passing tools directly
- When building a system with multiple agents, use the Factory and Orchestrator
- For dynamic requirements, use the DynamicAgentFactory
- When integrating with external APIs or services, leverage the MCP capabilities
- For computationally intensive operations, consider implementing external tools in languages like C/C++, Rust, or Go
