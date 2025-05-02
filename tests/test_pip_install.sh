#!/bin/bash

# Test script for verifying pip installation and observability features

# Create a temporary test directory
TEST_DIR=$(mktemp -d)
echo "Created test directory: $TEST_DIR"
cd "$TEST_DIR"

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install tinyAgent with traceboard
pip install tiny_agent_os[traceboard]

# Create test configuration
cat > config.yml << EOL
observability:
  tracing:
    enabled: true
    service_name: "test-tinyagent"
    sampling_rate: 1.0
    exporter:
      type: "sqlite"
      db_path: "test_traces.db"
    attributes:
      environment: "test"
      version: "0.1.0"
EOL

# Create test script
cat > test_observability.py << EOL
from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent
from tinyagent.observability.tracer import configure_tracing
import time

@tool
def greet(name: str) -> str:
    """Greet someone."""
    time.sleep(1)  # Add delay to make trace more interesting
    return f"Hello, {name}!"

def main():
    # Configure tracing
    configure_tracing()
    
    # Create traced agent
    agent = tiny_agent(tools=[greet], trace_this_agent=True)
    
    # Run the agent
    result = agent.run("Greet Alice")
    print(f"Agent result: {result}")

if __name__ == "__main__":
    main()
EOL

# Run the test script
python test_observability.py

# Launch traceboard in background
python -m tinyagent.observability.traceboard --db test_traces.db &
TRACEBOARD_PID=$!

# Wait for traceboard to start
sleep 2

# Try to access traceboard
if curl -s http://127.0.0.1:8000 > /dev/null; then
    echo "✅ Traceboard is accessible"
else
    echo "❌ Failed to access traceboard"
fi

# Cleanup
kill $TRACEBOARD_PID
deactivate
echo "Test complete. Check $TEST_DIR for artifacts." 