# Installing tinyAgent

**Made by (x) @tunahorse21 | A product of alchemiststudios.ai**

> **IMPORTANT**: tinyAgent is in EARLY BETA until V1. Use common sense when working with this tool.  
> NOT RESPONSIBLE FOR ANY ISSUES that may arise from its use.

This document provides detailed instructions for installing tinyAgent using either UV (recommended) or pip. Follow the installation method that best suits your environment and preferences.

## Prerequisites

Before installing tinyAgent, ensure you have the following:

- Python 3.9 or higher
- Node.js 18 or higher with npm 7+ (required for MCP server functionality)
  - Node.js download: [https://nodejs.org/](https://nodejs.org/)
  - To check your versions: `python --version && node --version && npm --version`
- Git (for cloning the repository)

## Required Configuration Files

tinyAgent requires two configuration files to operate properly:

### 1. Environment Variables (.env)

Create a `.env` file in the root directory with your API keys. You can copy the example file:

```bash
cp .envexample .env
```

Then edit the `.env` file to add your actual API keys:

```
# API Keys - Replace with your actual keys
OPENROUTER_API_KEY=your_openrouter_key_here
BRAVE=your_brave_key_here
OR_SITE_URL = "https://openrouter.ai"
OR_APP_NAME = "OpenRouter"
```

### 2. Configuration File (config.yml)

Create a `config.yml` file in the root directory or copy the example:

```bash
cp exampleconfig.yml config.yml
```

This file controls important settings like:
- Model selection
- Parsing options
- Rate limiting
- Dynamic agent configuration
- Security settings

Be sure to review the configuration settings, especially rate limits to prevent excessive API calls.


## Option 1: Installation with UV (Recommended)

[UV](https://github.com/astral-sh/uv) is a fast, reliable Python package installer and resolver. We recommend using UV for the best installation experience with tinyAgent.

### 1. Install UV

If you don't already have UV installed:

```bash
# On macOS or Linux
curl -fsSL https://astral.sh/uv/install.sh | bash

# On Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

### 2. Clone the Repository

```bash
git clone https://github.com/tinyagent/tinyagent.git
cd tinyagent
```

### 3. Create and Activate a Virtual Environment (Optional but Recommended)

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux
source .venv/bin/activate
# On Windows
.\.venv\Scripts\activate
```

### 4. Install Dependencies with UV

```bash
# Check UV installation
if ! command -v uv &> /dev/null; then
    echo "UV not found. Please install UV first (see step 1)"
    echo "curl -fsSL https://astral.sh/uv/install.sh | bash"
    exit 1
fi

# Install from pyproject.toml (recommended)
uv pip install -e . || {
    echo "UV installation failed. Try again with verbose output..."
    uv pip install -e . -v
}

# If you need specific dependencies including development tools
# uv pip install -e .[dev,llm]

# Alternative: install from requirements.txt if available
# uv pip install -r requirements.txt

# Verify installation
PYTHON_IMPORT_CHECK="import tinyagent; print('✅ tinyAgent installed successfully!')"
python -c "$PYTHON_IMPORT_CHECK" || echo "⚠️ tinyAgent package may not be installed correctly"
```

This will quickly resolve and install all dependencies. Using the pyproject.toml method ensures that you get exactly the right versions needed for compatibility.

### 5. Install Additional Dependencies for MCP

```bash
# Navigate to the MCP directory
cd mcp

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "npm is not installed. Please install Node.js (https://nodejs.org/)"
    echo "For Ubuntu/Debian: sudo apt install nodejs npm"
    echo "For macOS: brew install node"
    echo "For Windows: Download from https://nodejs.org/"
    exit 1
fi

# Check npm version
NPM_VERSION=$(npm -v | cut -d. -f1)
if [ "$NPM_VERSION" -lt 7 ]; then
    echo "Warning: npm version $NPM_VERSION detected. tinyAgent recommends npm 7 or higher."
    echo "Consider upgrading: npm install -g npm@latest"
fi

# Install Node.js dependencies with error handling
npm install || { echo "npm install failed. Trying with --no-fund --no-audit flags..."; npm install --no-fund --no-audit; }

# Build the MCP server with error handling
npm run build || { echo "Build failed. Checking TypeScript installation..."; npm install -g typescript && npm run build; }

# Verify installation was successful
if [ -d "build" ]; then
    echo "✅ MCP build completed successfully!"
else
    echo "⚠️ MCP build directory not found. The build may have failed."
fi

# Return to the main directory
cd ..
```

## Option 2: Installation with pip

If you prefer to use standard pip, follow these steps:

### 1. Clone the Repository

```bash
git clone https://github.com/tinyagent/tinyagent.git
cd tinyagent
```

### 2. Create and Activate a Virtual Environment

```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On macOS/Linux
source .venv/bin/activate
# On Windows
.\.venv\Scripts\activate
```

### 3. Install Dependencies with pip

```bash
# Check pip installation
if ! command -v pip &> /dev/null; then
    echo "pip not found. Installing pip..."
    python -m ensurepip --upgrade || {
        echo "Error installing pip. Please install pip manually."
        echo "https://pip.pypa.io/en/stable/installation/"
        exit 1
    }
fi

# Check pip version
PIP_VERSION=$(pip --version | grep -oP '\d+' | head -1)
if [ "$PIP_VERSION" -lt 20 ]; then
    echo "Warning: pip version $PIP_VERSION detected. Consider upgrading to pip 20+"
    echo "Run: pip install --upgrade pip"
    pip install --upgrade pip
fi

# Install from pyproject.toml in development mode (recommended)
pip install -e . || {
    echo "Standard installation failed. Trying with verbose output and without dependencies..."
    pip install -e . -v --no-dependencies && pip install -r requirements.txt
}

# Install with optional development and LLM dependencies if needed
# pip install -e .[dev,llm]

# Alternative: install from requirements.txt if available
# pip install -r requirements.txt

# Verify installation
PYTHON_IMPORT_CHECK="import tinyagent; print('✅ tinyAgent installed successfully!')"
python -c "$PYTHON_IMPORT_CHECK" || echo "⚠️ tinyAgent package may not be installed correctly"
```

#### Creating a requirements.txt from pyproject.toml

If you need to generate a requirements.txt file from the pyproject.toml:

```bash
# Using pip-tools
pip install pip-tools
pip-compile --output-file=requirements.txt pyproject.toml

# Alternatively, create a lockfile with uv and convert it
uv pip compile pyproject.toml -o requirements.txt
```

### 4. Install Additional Dependencies for MCP

```bash
# Navigate to the MCP directory
cd mcp

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "npm is not installed. Please install Node.js (https://nodejs.org/)"
    echo "For Ubuntu/Debian: sudo apt install nodejs npm"
    echo "For macOS: brew install node"
    echo "For Windows: Download from https://nodejs.org/"
    exit 1
fi

# Check npm version
NPM_VERSION=$(npm -v | cut -d. -f1)
if [ "$NPM_VERSION" -lt 7 ]; then
    echo "Warning: npm version $NPM_VERSION detected. tinyAgent recommends npm 7 or higher."
    echo "Consider upgrading: npm install -g npm@latest"
fi

# Install Node.js dependencies with error handling
npm install || { echo "npm install failed. Trying with --no-fund --no-audit flags..."; npm install --no-fund --no-audit; }

# Build the MCP server with error handling
npm run build || { echo "Build failed. Checking TypeScript installation..."; npm install -g typescript && npm run build; }

# Verify installation was successful
if [ -d "build" ]; then
    echo "✅ MCP build completed successfully!"
else
    echo "⚠️ MCP build directory not found. The build may have failed."
fi

# Return to the main directory
cd ..
```

## Configuration

### 1. Environment Variables

Create a `.env` file in the project root directory:

```bash
cp .env.example .env
```

Edit the `.env` file to add your API keys:

```bash
# OpenRouter API key (required)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Brave API key (optional, for web search)
BRAVE=your_brave_api_key_here

# Other API keys as needed
```

### 2. Configure tinyAgent

The `config.yml` file contains various configuration options for tinyAgent. You can customize this file to adjust:

- Model selection
- Security settings
- Rate limits
- Parsing options
- Dynamic agent settings

## Verify Installation

To verify your installation:

```bash
# Run the main CLI
python main.py

# You should see the tinyAgent banner and prompt
```

Try a simple command to test functionality:

```
calculate 2 + 2
```

## Troubleshooting

### Common Issues

#### 1. Python Dependency Issues

If you encounter errors about missing or incompatible Python packages:

```bash
# Using UV - reinstall with all dependencies
uv pip install -e .[dev,llm] --force-reinstall

# Using pip - reinstall with development dependencies
pip install -e .[dev] --force-reinstall

# Clear pip cache if needed
pip cache purge

# Check for conflicting packages
pip check
```

#### 2. Node.js/npm Issues

If you encounter errors with the MCP component:

```bash
# Check Node.js and npm versions
node --version  # Should be v18+
npm --version   # Should be v7+

# Clear npm cache
npm cache clean --force

# Install TypeScript globally if build fails
npm install -g typescript

# Manually install MCP dependencies
cd mcp
rm -rf node_modules package-lock.json
npm install
npm run build
```

#### 3. Import Errors

If you see "ModuleNotFoundError" when running tinyAgent:

```bash
# Verify that tinyAgent is correctly installed
python -c "import tinyagent; print('Success!')"

# If the import fails, try installing in development mode
pip install -e .

# Check your PYTHONPATH
echo $PYTHONPATH

# You can manually add the project directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/path/to/tinyagent
```

#### 4. Permission Issues

On Linux/macOS, you might encounter permission errors:

```bash
# Fix permission issues for the Python virtual environment
chmod -R 755 .venv/

# Fix permissions for script files
chmod +x *.sh
```
pip list
```

##### Common Dependency Problems:

- **Version conflicts**: Try installing with the `--no-deps` flag and then manually install the conflicting packages
- **Wheel build failures**: Ensure you have necessary build tools (gcc, python-dev, etc.)
- **Platform-specific packages**: Some packages may require OS-specific libraries

##### Fixing dependency issues with UV:

UV provides better dependency resolution:

```bash
# Clean your environment first
uv pip uninstall -y tinyagent

# Install with strict resolution
uv pip install -e . --strict
```

If specific packages are causing problems, try installing them separately:

```bash
uv pip install problematic-package==specific-version
```

#### 2. MCP Server Errors

If you encounter errors related to the MCP server:

```bash
# Rebuild the MCP server
cd mcp
npm install
npm run build
cd ..
```

#### 3. API Key Issues

If you see authentication errors:

- Verify your API keys in the `.env` file
- Ensure the `.env` file is in the project root directory
- Check that the API service is available and your key is valid

#### 4. Python Version Issues

tinyAgent requires Python 3.9 or higher. If you're using an older version, you'll need to upgrade:

```bash
# Check your Python version
python --version

# If it's below 3.9, install a newer version via your package manager
```

## Updates

To update tinyAgent to the latest version:

```bash
# Pull the latest changes
git pull

# Update dependencies
# With UV
uv pip install -r requirements.txt

# With pip
pip install -r requirements.txt

# Update MCP dependencies
cd mcp
npm install
npm run build
cd ..
```

## Development Installation

For development, you may want to install in editable mode:

```bash
# Using UV
uv pip install -e .

# Using pip
pip install -e .
```

## Next Steps

After installation:

1. Read the [README.md](README.md) for an overview of tinyAgent
2. Check out the [documentation](core/docs/README.md) for detailed information
3. Try the examples in the [cookbook](cookbook/cookbook.md)

## Support

If you encounter any issues with installation, please:

1. Check the [troubleshooting](#troubleshooting) section above
2. Search for existing issues on the GitHub repository
3. Open a new issue if your problem isn't already addressed
