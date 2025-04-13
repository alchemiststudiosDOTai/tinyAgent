---

# tinyAgent 🤖

![tinyAgent Logo](static/images/tinyAgent_logo_v2.png)

```
   __  .__                _____                         __
_/  |_|__| ____ ___.__. /  _  \    ____   ____   _____/  |_
\   __\  |/    <   |  |/  /_\  \  / ___\_/ __ \ /    \   __\
 |  | |  |   |  \___  /    |    \/ /_/  >  ___/|   |  \  |
 |__| |__|___|  / ____\____|__  /\___  / \___  >___|  /__|
              \/\/            \//_____/      \/     \/
```

**Made by (x) [@tunahorse21](https://x.com/tunahorse21) | A product of [alchemiststudios.ai](https://alchemiststudios.ai)**

---

## Heads Up

tinyAgent is in **BETA** until V1. It's working but still evolving! I can't guarantee it's 100% bug-free, but I'm actively improving it whenever I can between my day job and business.  
Found something that could be better? Show off your skills and open an issue with a fix: I'd genuinely appreciate it!

---

## Overview

tinyAgent is a streamlined framework for building powerful, LLM-powered agents that solve complex tasks through tool execution, orchestration, and dynamic capability creation. Convert any Python function into a useful tool and then into an agent with minimal configuration, unlocking a world of scalable, modular possibilities.

---

## Installation

### Via pip (Recommended)

```bash
pip install tiny_agent_os
```

---

## Post-Installation Configuration for Pip Users

After installing via `pip`, you'll need to provide your own configuration files. For convenience, you can download the defaults directly:

---

### Download the Configuration File (`config.yml`)

**Using `wget`:**

```bash
wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/config.yml
```

---

### Download the Environment File (`.env`)

Download the example environment file and rename it to `.env`:

**Using `wget`:**

```bash
wget https://raw.githubusercontent.com/alchemiststudiosDOTai/tinyAgent/v0.65/.envexample -O .env
```

> **Note:** Be sure to edit the `.env` file with your actual API keys and any other required variables.

---

### Cloning for Development

```bash
git clone https://github.com/alchemiststudiosDOTai/tinyAgent.git
cd tinyAgent
```

---

## Post-Installation Configuration

After installing (either via pip or from source), remember to configure your environment and `.env` files with relevant API keys from https://openrouter.ai

Both the config.yml and env work out of the box with a openrouter API, you can use any openai API, and the config has an example of a local LLM.
The /documentation folder has more details and is being updated.

---

## Tools and the `@tool` Decorator

In tinyAgent, **any Python function** can be transformed into a usable "tool" by simply decorating it with `@tool`. This makes it discoverable by your agents, allowing them to execute that function in response to natural-language queries.

### Example

```python
from tinyagent.decorators import tool

@tool
def greet_person(name: str) -> str:
    """Return a friendly greeting."""
    return f"Hello, {name}!"
```

That's it! Once decorated, `greet_person` can be included in an agent's list of tools, letting your LLM-driven agent call it as needed.

---

## Philosophy

tinyAgent is built on two core ideas:

### 1. Functions as Agents

Any Python function can be turned into a tool—and then seamlessly integrated into an agent. This approach makes extending and innovating simple.

```mermaid
flowchart LR
    A["Python Function"] --> B["Tool"]
    B --> C["Agent"]
    C --> D["Result"]
```

![Function to Agent Flow](static/images/func_agent.png)

```python
#!/usr/bin/env python3
"""
Example: Functions as Agents
"""
from tinyagent.decorators import tool
from tinyagent.factory.agent_factory import AgentFactory

@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b

def main():
    agent = AgentFactory.get_instance().create_agent(tools=[calculate_sum])
    query = "calculate the sum of 5 and 3"
    print(f"Query: '{query}'")
    result = agent.run(query, expected_type=int)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
```

### 2. tiny_chain Orchestration

Complex tasks are handled through an intelligent chain of tools that automatically:

- Selects appropriate tools
- Maintains context between steps
- Processes results in sequence

```mermaid
flowchart LR
    A["Task"] --> B["tiny_chain"]
    B --> C["Search Tool"]
    B --> D["Browser Tool"]
    B --> E["Summarize Tool"]
    C --> F["Context"]
    D --> F
    E --> F
    F --> G["Result"]

    style B fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#bbf,stroke:#333,stroke-width:2px
```

```python
from tinyagent.factory.tiny_chain import tiny_chain
from tinyagent.tools.duckduckgo_search import get_search_tool
from tinyagent.tools.custom_text_browser import get_browser_tool
from tinyagent.decorators import tool

@tool(name="summarize")
def summarize_text(text: str) -> str:
    """Summarize the provided text."""
    return llm_summarize(text)  # Your LLM summarization logic

# Create chain with tools
chain = tiny_chain.get_instance(tools=[
    get_search_tool(),      # Search the web
    get_browser_tool(),     # Visit and extract content
    summarize_text._tool    # Summarize findings
])

# Execute complex task
task_id = chain.submit_task(
    "research latest AI developments and summarize key points"
)

# Get results
status = chain.get_task_status(task_id)
if status.result:
    for step in status.result['steps']:
        print(f"Step {step['tool']}: {step['result']}")
```

---

## Features

- **Modular Design:** Easily convert any function into a tool.
- **Flexible Agent Options:** Use the simple orchestrator or advanced `AgentFactory`.
- **Robust Error Handling:** Improved debugging with custom exceptions.
- **Structured Output:** Enforce JSON formats for consistent outputs.

---

## Acknowledgments & Inspirations

- **my wife**
- [HuggingFace SmoLAgents](https://github.com/huggingface/smolagents)
- [Aider-AI](https://github.com/Aider-AI/aider)
- And many other open-source contributors!

---

## Contact

For questions, suggestions, or business inquiries:

- **Email**: [info@alchemiststudios.ai](mailto:info@alchemiststudios.ai)
- **X**: [@tunahorse21](https://x.com/tunahorse21)
- **Website**: [alchemiststudios.ai](https://alchemiststudios.ai)

---

## License

**Business Source License 1.1 (BSL)**  
This project is licensed under the Business Source License 1.1. It is **free for individuals and small businesses** (with annual revenues under $1M).  
For commercial use by larger businesses, an enterprise license is required.  
For licensing or usage inquiries, please contact: [info@alchemiststudios.ai](mailto:info@alchemiststudios.ai)
