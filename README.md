# tinyAgent 🤖

A streamlined framework for building powerful LLM-powered agents that can solve complex tasks through tool execution, orchestration, and dynamic capability creation.

**Made by (x) @tunahorse21 | A product of alchemiststudios.ai**

> **IMPORTANT**: tinyAgent is in EARLY BETA until V1. Use common sense when working with this tool.  
> NOT RESPONSIBLE FOR ANY ISSUES that may arise from its use.
> I made this becuase I wanted to, I work fulltime + business, bugs will be fixed asap but expect some issues until V1
> Nerds, please don't get mad, instead show me how "cracked" you are and open an issue with a fix ! 

![tinyAgent Logo](tintAgentLogo.png)

```
   __  .__                _____                         __   
_/  |_|__| ____ ___.__. /  _  \    ____   ____   _____/  |_ 
\   __\  |/    <   |  |/  /_\  \  / ___\_/ __ \ /    \   __\
 |  | |  |   |  \___  /    |    \/ /_/  >  ___/|   |  \  |  
 |__| |__|___|  / ____\____|__  /\___  / \___  >___|  /__|  
              \/\/            \//_____/      \/     \/      
 tinyAgent: 

### Installation

```bash
# Clone the repository
git clone https://github.com/alchemiststudiosDOTai/tinyAgent.git

cd tinyagent

# Option 1: For Linux users, run the installation script
chmod +x install/linuxInstall.sh && ./install/linuxInstall.sh

# Option 2: Manual installation
# Create a virtual environment (recommended)
python3 -m venv .venv

# Activate the virtual environment
# On macOS/Linux
source .venv/bin/activate
# On Windows
.\.venv\Scripts\activate

# Install dependencies
# Option 1: Using UV (recommended - see INSTALL.md for details)
# Option 2: Using pip
pip install -r requirements.txt

# Set up required configuration files
# 1. Environment variables
cp .envexample .env
# Edit .env to add your API keys (especially OpenRouter)

# 2. Configuration file
cp exampleconfig.yml config.yml
# Edit config.yml to customize your settings
```
---
## Philosophy
### 1. Functions as Agents
### 2. Hierarchical Orchestra of Specialized Agents
### 3. Dynamic Capability Creation

The **tinyAgent** framework is designed to simplify building and managing AI-driven agents that perform tasks and interact with tools. It provides three methods for creating agents—`Orchestrator`, `AgentFactory`, and `DynamicAgentFactory`—each tailored to different needs, from simple workflows to complex, dynamic setups. Agents can register tools, manage workflows, and maintain context, with key features like:

- **High-level Orchestrator**: Easy task management.
- **AgentFactory**: Detailed control over agent setup and tools.
- **DynamicAgentFactory**: On-the-fly creation of specialized agents.
- **Tool Decorators**: Simple tool registration with `@tool`.
- **Structured Results**: Consistent tool output handling.
- **Error Handling and Logging**: Built-in for reliability.

---

## Installation

Here’s how to install and set up **tinyAgent**:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-repo/tinyAgent.git
   cd tinyAgent
   ```

2. **Install Dependencies**:
   - Requires Python 3.8+.
   - Install packages:
     ```bash
     pip install -r requirements.txt
     ```

3. **Configure Settings**:
   - Copy the example config:
     ```bash
     cp config.example.yaml config.yaml
     ```
   - Update `config.yaml` with your model details, API keys, etc.

4. **Optional: Use a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

Check the [official docs](https://github.com/your-repo/tinyAgent/blob/main/docs/installation.md) for more details.

---

## Benefits

1. **Modular Design**  
   - Tools are defined with `@tool` and easily integrated or swapped.

2. **Flexible Agent Options**  
   - **Orchestrator**: Simple task execution.  
   - **AgentFactory**: Fine-tuned control.  
   - **DynamicAgentFactory**: Dynamic agent creation.

3. **Centralized Setup**  
   - Factory pattern streamlines configuration and logging.

4. **Robust Error Handling**  
   - Custom exceptions (e.g., `ToolError`) improve debugging.

5. **Clean Code Structure**  
   - Agents handle logic; tools handle execution.

6. **Versatile Interaction**  
   - Use `agent.execute_tool()` for precision or `agent.run()` for broader tasks.


---
## Roadmap of Improvements

tinyAgent is actively evolving with several planned improvements:

### Near-term (0-3 months)
- ✅ **Configurable Security**: Enhanced security options for code execution (recently implemented)
- 🔄 **Memory and Context Management**: Improved handling of conversation history and context
- 🔄 **Multi-modal Support**: Better handling of images, audio, and other non-text inputs
- 🔄 **Tool Chaining Improvements**: More robust tool chaining capabilities

### Mid-term (3-6 months)
- 📝 **Advanced Orchestration Patterns**: More sophisticated task routing and agent collaboration
- 📝 **Expanded Model Provider Support**: Integration with more LLM providers and models
- 📝 **Performance Optimization**: Caching, parallelization, and other performance improvements
- 📝 **Test Framework**: Comprehensive test suite for agent behavior validation

### Long-term (6+ months)
- 🔮 **Web Interface/Dashboard**: Graphical interface for monitoring and managing agents
- 🔮 **Tool Marketplace**: Community-contributed tools ecosystem
- 🔮 **Multi-agent Collaboration**: Enhanced collaboration between specialized agents
- 🔮 **Learning and Adaptation**: Agents that improve over time based on usage patterns

---
## Acknowledgments & Inspo
We'd like to thank the creators of these amazing projects that inspired TinyAgent:
- My Wife
- [HuggingFace SmoLAgents](https://github.com/huggingface/smolagents)
- [Aider-AI](https://github.com/Aider-AI/aider)
- [Kyon-eth](https://github.com/kyon-eth)
- [RA.Aid](https://github.com/ai-christianson/RA.Aid)
---
## Contributing

Contributions to tinyAgent are welcome! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.
---
## Key Takeaways

- **tinyAgent** is perfect for scalable AI projects needing structured agent and tool management.
- It offers **extensibility**, **error handling**, and **logging**, but may be overkill for simple tasks.

*Important Note on Tools**: 

The aider tool integrated in TinyAgent is extremely powerful but requires proper understanding to use effectively. It's highly configurable with many advanced features that can dramatically enhance productivity when used correctly.

**⚠️ We strongly recommend thoroughly learning aider before using it in any serious projects.** 

Invest time in studying the documentation at https://aider.chat/ to understand its capabilities, configuration options, and best practices. This investment will pay off significantly in your development workflow.

