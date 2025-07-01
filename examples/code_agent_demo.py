"""
TinyCodeAgent Demo - Python-executing ReAct agent

This example demonstrates:
1. Basic calculations with Python
2. Using tools within Python code
3. Multi-step reasoning with observations
4. Working with allowed imports (math)
"""

from tinyagent import TinyCodeAgent, tool


# Define some tools the agent can use
@tool
def search_web(query: str) -> str:
    """Search the web for information.

    Args:
        query: Search query string

    Returns:
        str: Search results as text

    Example:
        search_web('Tokyo population')
        # Returns: "Tokyo's population is approximately 13.96 million..."
    """
    # Mock implementation
    if "population" in query.lower() and "tokyo" in query.lower():
        return "Tokyo's population is approximately 13.96 million in the city proper, and 37.4 million in the greater metropolitan area."
    elif "speed of light" in query.lower():
        return "The speed of light in vacuum is 299,792,458 meters per second (approximately 300,000 km/s)."
    return f"No results found for: {query}"


@tool
def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Returns dict with keys:
    - temp: int (temperature in Celsius)
    - condition: str (e.g. 'Partly cloudy', 'Sunny', 'Rainy')
    - humidity: int (percentage 0-100)

    Example:
        get_weather('Tokyo')
        # Returns: {"temp": 22, "condition": "Partly cloudy", "humidity": 65}
    """
    # Mock implementation
    weather_data = {
        "Tokyo": {"temp": 22, "condition": "Partly cloudy", "humidity": 65},
        "New York": {"temp": 18, "condition": "Sunny", "humidity": 45},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 80},
    }
    return weather_data.get(city, {"temp": 20, "condition": "Unknown", "humidity": 50})


@tool
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in kilometers."""
    # Simplified calculation (not using Haversine for demo)
    import math

    # Rough approximation
    lat_diff = abs(lat2 - lat1)
    lon_diff = abs(lon2 - lon1)
    distance = math.sqrt(lat_diff**2 + lon_diff**2) * 111  # rough km per degree
    return round(distance, 2)


def main():
    # You can specify any OpenRouter model
    agent = TinyCodeAgent(
        tools=[search_web, get_weather, calculate_distance],
        model="gpt-4o-mini",  # or "anthropic/claude-3.5-haiku", "meta-llama/llama-3.2-3b-instruct"
        extra_imports=["math"],
    )

    print("TinyCodeAgent Demo")
    print("=" * 50)

    # Example 1: Simple calculation
    print("\n1. Simple calculation:")
    answer = agent.run("What is the cube root of 987654321?", verbose=True)
    print(f"Answer: {answer}")

    # Example 2: Using tools with schema
    print("\n2. Weather analysis:")
    answer = agent.run(
        "Compare the weather in Tokyo and London. Which city has better conditions for outdoor activities?",
        verbose=True,
    )
    print(f"Answer: {answer}")

    # Example 3: Multi-step reasoning
    print("\n3. Population density calculation:")
    answer = agent.run(
        "Search for Tokyo's population and calculate how many people per square kilometer if Tokyo's area is 2,194 square kilometers.",
        verbose=True,
    )
    print(f"Answer: {answer}")


if __name__ == "__main__":
    main()
