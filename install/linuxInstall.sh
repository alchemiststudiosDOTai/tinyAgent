#!/usr/bin/env bash

# tinyAgent Linux Installation Script
# This script is for Linux installations only

set -e  # Exit immediately if a command exits with a non-zero status

echo "===================================================="
echo "   tinyAgent Linux Installation Script"
echo "   Made by (x) @tunahorse21 | alchemiststudios.ai"
echo "===================================================="
echo ""
echo "IMPORTANT: This script is for Linux installations only."
echo ""

# Check if running on Linux
if [[ "$(uname)" != "Linux" ]]; then
    echo "ERROR: This script is intended for Linux systems only."
    echo "For other operating systems, please follow the manual installation instructions in INSTALL.md."
    exit 1
fi

# Project root directory (where the script is run from)
ROOT_DIR=$(pwd)
echo "Installing tinyAgent in $ROOT_DIR"

# Create virtual environment
echo "\n[1/5] Creating Python virtual environment..."
python3 -m venv .venv || {
    echo "ERROR: Failed to create virtual environment. Make sure python3-venv is installed."
    echo "On Ubuntu/Debian, run: sudo apt install python3-venv"
    exit 1
}

# Activate virtual environment
echo "[2/5] Activating virtual environment..."
source .venv/bin/activate || {
    echo "ERROR: Failed to activate virtual environment."
    exit 1
}

# Install Python dependencies
echo "[3/5] Installing Python dependencies..."
pip install -r requirements.txt || {
    echo "ERROR: Failed to install Python dependencies."
    exit 1
}

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed. It's required for MCP functionality."
    echo "Please install Node.js (https://nodejs.org/) and run this script again."
    echo "For Ubuntu/Debian: sudo apt install nodejs npm"
    exit 1
fi

# Install npm dependencies
echo "[4/5] Installing npm dependencies for MCP..."
cd "$ROOT_DIR/mcp" || {
    echo "ERROR: MCP directory not found."
    exit 1
}

npm install || {
    echo "ERROR: Failed to install npm dependencies."
    exit 1
}

# Build MCP server
echo "[5/5] Building MCP server..."
npm run build || {
    echo "ERROR: Failed to build MCP server."
    exit 1
}

cd "$ROOT_DIR"

# Set up configuration files if they don't exist
if [ ! -f .env ]; then
    echo "Creating example .env file..."
    cp .envexample .env
    echo "\nIMPORTANT: Edit the .env file to add your API keys:\n"
    echo "  - OPENROUTER_API_KEY: Required for accessing LLM models"
    echo "  - BRAVE: Optional for Brave Search functionality"
 fi

if [ ! -f config.yml ]; then
    echo "Creating example config.yml file..."
    cp exampleconfig.yml config.yml
fi

# New addition: Automatically activate venv and start main.py
echo "\nActivating virtual environment and starting tinyAgent..."
source .venv/bin/activate
echo "Starting tinyAgent (main.py)..."
python3 main.py

echo "\n===================================================="
echo "tinyAgent installation completed successfully!"
echo "\nTo activate the environment and start using tinyAgent:"
echo "    source .venv/bin/activate"
echo "    python main.py"
echo "\nRemember to edit your .env file to add your API keys."
echo "See INSTALL.md for more details."
echo "===================================================="
