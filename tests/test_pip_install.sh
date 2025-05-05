#!/bin/bash

# Test script for verifying pip installation and observability features

# Check if required API keys are available
if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "⚠️ OPENROUTER_API_KEY is not set. Tests requiring OpenRouter API will fail."
  echo "Please set a valid API key before running this script:"
  echo "export OPENROUTER_API_KEY='your-key-here'"
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "⚠️ OPENAI_API_KEY is not set. Tests requiring OpenAI API will fail."
  echo "Please set a valid API key before running this script:"
  echo "export OPENAI_API_KEY='your-key-here'"
fi

# Create a temporary test directory
TEST_DIR=$(mktemp -d)
echo "Created test directory: $TEST_DIR"
cd "$TEST_DIR"

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install tinyAgent with traceboard
pip install tiny_agent_os[traceboard]

# Install testing dependencies
echo "Installing testing dependencies..."
pip install pytest opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp chromadb anyio==4.0.0 sentence-transformers

# Run all tests with pytest
echo "Running all tests using pytest..."
cd -  # Return to original directory

# Run all the tests in one command
echo "==========================================="
echo "Running all tests at once"
pytest -xvs tests/0[0-7]_*.py
TEST_RESULT=$?
echo "==========================================="

# Report test results
if [ $TEST_RESULT -ne 0 ]; then
    echo "❌ Some tests failed."
    echo "Note: API-dependent tests require valid API keys to be set in the environment."
    echo "You may need to set valid OPENROUTER_API_KEY and OPENAI_API_KEY values."
else
    echo "✅ All tests passed!"
fi

# Return to test directory to cleanup
cd "$TEST_DIR"
deactivate
echo "Test complete. Check $TEST_DIR for artifacts." 