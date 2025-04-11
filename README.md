

⸻

tinyAgent 🤖

![tinyAgent Logo](tintAgentLogo.png)

   __  .__                _____                         __
_/  |_|__| ____ ___.__. /  _  \    ____   ____   _____/  |_
\   __\  |/    <   |  |/  /_\  \  / ___\_/ __ \ /    \   __\
 |  | |  |   |  \___  /    |    \/ /_/  >  ___/|   |  \  |
 |__| |__|___|  / ____\____|__  /\___  / \___  >___|  /__|
              \/\/            \//_____/      \/     \/

Made by (x) @tunahorse21 | A product of alchemiststudios.ai

⸻

Heads Up

tinyAgent is in BETA until V1. It’s working but still evolving! I can’t guarantee it’s 100% bug-free, but I’m actively improving it whenever I can between my day job and business.
Found something that could be better? Show off your skills and open an issue with a fix: I’d genuinely appreciate it!

⸻

Table of Contents
	•	Overview
	•	Installation
	•	Via pip (Recommended)
	•	Cloning for Development
	•	Post-Installation Configuration for Pip Users
	•	Example Usage
	•	Tools and the @tool Decorator
	•	Brief Overview of Creating a Tool
	•	Example: Calculator Tool
	•	Philosophy
	•	Functions as Agents
	•	Hierarchical Orchestration
	•	Features
	•	Acknowledgments & Inspirations
	•	Contact
	•	License

⸻

Overview

tinyAgent is a streamlined framework for building powerful, LLM powered agents that solve complex tasks through tool execution, orchestration, and dynamic capability creation. Convert any Python function into a useful tool and then into an agent with minimal configuration, which opens up a world of scalable, modular possibilities for your projects.

⸻

Installation

Via pip (Recommended)

Install tinyAgent easily with a single command:

pip install tiny_agent_os

Cloning for Development

To clone the repository and contribute or experiment directly:

git clone https://github.com/alchemiststudiosDOTai/tinyAgent.git
cd tinyAgent

For Linux Users

Run the provided installation script:

chmod +x install/linuxInstall.sh && ./install/linuxInstall.sh

Manual Installation
	1.	Create a Virtual Environment (Recommended):

python3 -m venv .venv


	2.	Activate the Virtual Environment:
	•	On macOS/Linux:

source .venv/bin/activate


	•	On Windows:

.\.venv\Scripts\activate


	3.	Install Dependencies:

pip install -r requirements.txt


	4.	Set Up Required Configuration Files:
Copy the example configuration files:

cp exampleconfig.yml config.yml
cp .envexample .env

Then, edit config.yml and .env to customize your settings and add your API keys (especially for OpenRouter).

⸻

Post-Installation Configuration for Pip Users

After installing via pip, you need to provide your own configuration files. For convenience, download them directly:

Download the Configuration File (config.yml)

Using wget:

wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/config.yml

Or using curl:

curl -O https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/config.yml

Download the Environment File (.env)

Download the example environment file (renaming it to .env is required):

Using wget:

wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/.envexample -O .env

Or using curl:

curl -o .env https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/.envexample

Note: Be sure to edit the .env file with your actual API keys and any other necessary variables.

⸻

Example Usage

The following example demonstrates the heart of tinyAgent: turning a simple function into a fully capable agent.

#!/usr/bin/env python3
"""
Example: Functions as Agents

This example shows how to convert a simple function into a tool with tinyAgent.
"""
from tinyagent.decorators import tool
from tinyagent.factory.agent_factory import AgentFactory

# Define a simple calculator function and turn it into a tool
@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

def main():
    """Create a basic agent with the calculator tool."""
    # Create an agent with our tool
    agent = AgentFactory.get_instance().create_agent(tools=[calculate_sum])
    query = "calculate the sum of 5 and 3"
    print(f"Running agent with query: '{query}'")
    result = agent.run(query, expected_type=int)  # Expect an integer result
    print(f"Result: {result}")
    print(f"Result Type: {type(result)}")

if __name__ == "__main__":
    main()



⸻

Tools and the @tool Decorator

tinyAgent’s power comes from tools—Python functions that can be transformed into agent-accessible functionality. By simply decorating a function with @tool, you make it discoverable and usable by the agent.

Brief Overview of Creating a Tool
	1.	Import the tool Decorator

from tinyagent.decorators import tool


	2.	Define Your Function
	•	Provide clear docstrings describing inputs, outputs, and function purpose.
	3.	Decorate Your Function

@tool
def my_function(arg1: str, arg2: int) -> bool:
    """Explain what this tool does, the expected input, and output."""
    # Implementation details here
    return True


	4.	Use in an Agent
	•	Create or obtain an instance of your agent and pass in your newly decorated function as a tool. The agent can now discover and utilize it to accomplish tasks.

Example: Calculator Tool

Below is an example of turning a basic calculator function (like the calculate_sum function) into a tool using the @tool decorator:

from tinyagent.decorators import tool
from tinyagent.factory.agent_factory import AgentFactory

@tool
def calculate_sum(a: int, b: int) -> int:
    """
    Calculate the sum of two integers.

    :param a: First integer
    :param b: Second integer
    :return: Sum of a and b
    """
    return a + b

def main():
    # Create an agent with our calculator tool
    agent = AgentFactory.get_instance().create_agent(tools=[calculate_sum])
    # The agent can now interpret instructions like "add X and Y"
    result = agent.run("What is the sum of 10 and 4?", expected_type=int)
    print(result)

if __name__ == "__main__":
    main()

Using the @tool decorator is all it takes to convert any Python function into a powerful building block for your agent’s capabilities.

⸻

Philosophy

tinyAgent is built on two core ideas:

Functions as Agents

Any Python function can be transformed into a tool—and then seamlessly integrated into an agent. This approach makes extending and innovating simple. Just tag your functions with the @tool decorator and let tinyAgent do the rest.

flowchart LR
    A["Python Function"] --> B["Tool"]
    B --> C["Agent"]
    C --> D["Result"]

![Function to Agent Flow](static/images/func_agent.png)

Hierarchical Orchestration

For more complex tasks, tinyAgent allows multiple agents to work together. A master orchestrator can delegate work to specialized agents—such as web search, summarization, or code snippet agents—to solve problems step-by-step.

NOTE: This is still in early development 

flowchart TD
    O["Research Orchestrator"] --> A1["Web Search Agent"]
    O --> A2["Summarizer Agent"]
    O --> A3["Code Snippet Agent"]



⸻

Features
	•	Modular Design: Easily convert any function into a tool using the @tool decorator.
	•	Flexible Agent Options: Leverage simple orchestrators, fine-tuned control with AgentFactory, or dynamic agent creation.
	•	Centralized Setup: Configure the framework using environment variables and configuration files.
	•	Robust Error Handling: Benefit from improved debugging with custom exceptions (e.g., ToolError).
	•	Versatile Interaction: Choose precise tool execution via agent.execute_tool() or broader command execution with agent.run().
	•	Structured Output: Optionally enforce JSON formatting for consistent, structured responses.

⸻

Acknowledgments & Inspirations

A big thank you goes out to everyone who has inspired and contributed to tinyAgent.
	•	My Wife
	•	HuggingFace SmoLAgents
	•	Aider-AI
	•	Kyon-eth
	•	RA.Aid

⸻

Contact

For questions, suggestions, or business inquiries:
	•	Email: info@alchemiststudios.ai
	•	X: @tunahorse21
	•	Website: alchemiststudios.ai

⸻

License

Business Source License 1.1 (BSL)
This project is licensed under the Business Source License 1.1. It is free for individuals and small businesses (with annual revenues under $1M).
For commercial use by larger businesses, an enterprise license is required.
For licensing or usage inquiries, please contact: info@alchemiststudios.ai.

⸻
