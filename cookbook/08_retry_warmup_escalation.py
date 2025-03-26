"""
Retry Warmup Escalation (RWE) Demo

This example demonstrates the enhanced retry system with:
1. Temperature warming
2. Model escalation
3. Detailed retry tracking

The agent will progressively:
- Increase temperature for creativity
- Escalate to more capable models
- Track and report all retry attempts
"""

import os
import sys
import json
from typing import Dict, Any
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import Agent
from core.config import load_config

def create_demo_config() -> Dict[str, Any]:
    """Create a demo configuration with retry settings."""
    base_config = load_config()
    
    # Add retry-specific configuration
    base_config.update({
        'retries': {
            'max_attempts': 3,
            'temperature': {
                'initial': 0.2,
                'increment': 0.2,
                'max': 0.8
            },
            'model_escalation': {
                'enabled': True,
                'sequence': [
                    "deepseek/deepseek-chat",      # Basic model
                    "anthropic/claude-3.5-sonnet",  # Better model
                    "anthropic/claude-3.7-sonnet"   # Best model
                ]
            }
        }
    })
    
    return base_config

class FailingAnalyzer:
    """A tool that fails the first two times to demonstrate retry behavior."""
    
    def __init__(self):
        self.attempts = 0
        
    def analyze(self, text: str) -> str:
        self.attempts += 1
        
        if self.attempts == 1:
            raise ValueError("First attempt: Basic model failed to understand complex quantum mechanics")
        elif self.attempts == 2:
            raise ValueError("Second attempt: Better model struggled with parallel universe concepts")
        else:
            return f"Final Analysis (Best Model): Successfully analyzed {text}"

def demo_retry_sequence(agent: Agent) -> None:
    """Run a sequence that demonstrates all retry stages."""
    
    # Create our failing analyzer
    analyzer = FailingAnalyzer()
    
    # Register the tool with the agent
    agent.create_tool(
        name="analyze",
        description="Analyze complex scientific concepts",
        func=analyzer.analyze,
        parameters={"text": "The text to analyze"}
    )
    
    try:
        print("\n=== Starting Analysis ===")
        result = agent.run(
            "Please analyze the quantum entanglement implications of "
            "using a neural network to predict weather patterns in "
            "a fifth-dimensional space while considering the butterfly effect "
            "in parallel universes where time flows backwards."
        )
        print("\n=== Final Success ===")
        print(f"Result: {result}")
        
    except Exception as e:
        print("\n=== Analysis Failed ===")
        print(f"Final Error: {str(e)}")
        if hasattr(e, 'history'):
            print("\n=== Retry History ===")
            for attempt in e.history:
                print(f"\nAttempt {attempt['attempt']}:")
                print(f"Model: {attempt.get('model', 'unknown')}")
                print(f"Temperature: {attempt.get('temperature', 'unknown')}")
                print(f"Error: {attempt.get('error', 'unknown')}")

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load demo config
    config = create_demo_config()
    
    # Create agent with demo config
    agent = Agent(config=config)
    
    # Print demo header
    print("\n=== RWE Demo ===")
    print("This will demonstrate the retry system with:")
    print("1. Temperature warming (0.2 → 0.4 → 0.6)")
    print("2. Model escalation (basic → better → best)")
    print("3. Detailed retry tracking")
    
    # Run the demo
    demo_retry_sequence(agent)

if __name__ == "__main__":
    main() 