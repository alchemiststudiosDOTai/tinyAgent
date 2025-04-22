from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent

@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b


def main():
    # Create an agent with the calculate_sum tool
    agent = tiny_agent(tools=[calculate_sum])
    query = "calculate the sum of 5 and 3"
    result = agent.run(query, expected_type=int)
    print(f"Query: '{query}' -> Result: {result}")


if __name__ == "__main__":
    main()

