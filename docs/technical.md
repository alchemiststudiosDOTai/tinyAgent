# tinyAgent Technical Details

## 1. Development Environment & Stack

- **Primary Language:** Python (Requires version 3.8+)
- **Package Manager:** `pip` (or optionally `uv` as mentioned in `INSTALL.md` - _needs verification_)
- **Configuration:** YAML (`config.yml`) for core settings, `.env` file for environment variables (API keys).
- **Virtual Environment:** Recommended (e.g., `python3 -m venv .venv`)

## 2. Installation

1.  **Clone Repository:**
    ```bash
    git clone https://github.com/alchemiststudiosDOTai/tinyAgent.git
    cd tinyAgent
    ```
2.  **Create & Activate Virtual Environment (Recommended):**

    ```bash
    # Create
    python3 -m venv .venv

    # Activate (macOS/Linux)
    source .venv/bin/activate
    # Activate (Windows)
    # .\.venv\Scripts\activate
    ```

3.  **Install Dependencies:**

    ```bash
    # Option 1: Using pip (standard)
    pip install -r requirements.txt

    # Option 2: Using UV (alternative - see INSTALL.md)
    # uv pip install -r requirements.txt
    ```

    _Note: The primary dependency file is `requirements.txt`._

4.  **Linux Specific Installation (Optional):**
    An installation script is provided for Linux users:
    ```bash
    chmod +x install/linuxInstall.sh && ./install/linuxInstall.sh
    ```

## 3. Configuration

1.  **Environment Variables:**

    - Copy the example: `cp .envexample .env`
    - Edit `.env` to add necessary API keys (e.g., OpenRouter key).

2.  **Core Configuration File:**
    - Copy the example: `cp exampleconfig.yml config.yml`
    - Edit `config.yml` to customize agent settings, model choices, logging levels, etc.

## 4. Key Technical Decisions & Patterns (Initial)

- **Decorator Pattern:** Used (`@tool`) for registering tools with agents, promoting modularity.
- **Factory Pattern:** Employed (`AgentFactory`, `DynamicAgentFactory`) for agent creation and centralized setup.
- **Structured Output:** Tools are expected to return results in a consistent format (details TBD).
- **Custom Exceptions:** Used for improved error handling (e.g., `ToolError` - _needs verification in codebase_).

_(Note: This document is based on the initial README.md. Specific dependencies, patterns, and technical constraints will be detailed further as development progresses.)_
