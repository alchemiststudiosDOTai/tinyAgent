from tinyagent import ReactAgent, tool  # ← only two imports


@tool  # registers metadata but returns the same function
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@tool
def divide(a: float, b: float) -> float:
    """Divide the first number by the second number."""
    return a / b


# ergonomic: just hand the funcs to the agent
agent = ReactAgent(tools=[multiply, divide])  # no registry lookup needed
print(agent.run("What is 12 times 5, then divided by 3?"))  # → 20
