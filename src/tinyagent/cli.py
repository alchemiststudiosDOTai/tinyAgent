#!/usr/bin/env python
"""
tinyAgent - A simple yet powerful framework for building LLM-powered agents.

This is the main entry point for the tinyAgent framework. It provides access to
all the core components of the framework through a clean, simple API.
"""

# Load environment variables first
from dotenv import load_dotenv

from tinyagent import CLI  # Core components

load_dotenv()

# Built-in tools

# Run CLI if executed directly
if __name__ == "__main__":
    # Call the core CLI implementation
    CLI()
