"""
Example showing how to use different models with TinyCodeAgent
"""

from tinyagent import TinyCodeAgent, tool


@tool
def calculate(expression: str) -> float:
    """Safely evaluate a mathematical expression."""
    # Only allow safe math operations
    allowed_names = {
        k: v for k, v in __builtins__.items() if k in ["abs", "round", "min", "max", "sum", "pow"]
    }
    allowed_names["__builtins__"] = {}
    return eval(expression, allowed_names)


def test_model(model_name: str, task: str):
    """Test a specific model with a task."""
    print(f"\n{'='*60}")
    print(f"Testing model: {model_name}")
    print(f"{'='*60}")

    agent = TinyCodeAgent(
        tools=[calculate],
        model=model_name,
        extra_imports=["math"],
    )

    try:
        result = agent.run(task, max_steps=3)
        print(f"✓ Result: {result}")
    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    task = "Calculate the sum of squares of the first 5 prime numbers (2, 3, 5, 7, 11)"

    # Test different models
    models = [
        "gpt-4o-mini",  # OpenAI
        "anthropic/claude-3.5-haiku",  # Anthropic
        "meta-llama/llama-3.2-3b-instruct",  # Meta
        "qwen/qwen-2.5-7b-instruct",  # Qwen
    ]

    print(f"Task: {task}")

    for model in models:
        test_model(model, task)


if __name__ == "__main__":
    main()
