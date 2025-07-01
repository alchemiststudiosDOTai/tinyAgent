"""
ReactAgent Demo - Showcasing scratchpad, error recovery, and observations

This example demonstrates:
1. Scratchpad thinking
2. Argument validation and recovery
3. Observation vs Error distinction
4. Output truncation
5. Graceful step limit handling
"""

from tinyagent import ReactAgent, tool


@tool
def get_weather(city: str) -> dict:
    """Get current weather for a city.

    Returns dict with keys:
    - temp: int (temperature in Celsius)
    - condition: str (e.g. 'Partly cloudy', 'Sunny', 'Rainy')
    - humidity: int (percentage 0-100)
    """
    weather_data = {
        "Tokyo": {"temp": 22, "condition": "Partly cloudy", "humidity": 65},
        "New York": {"temp": 18, "condition": "Sunny", "humidity": 45},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 80},
    }
    return weather_data.get(city, {"temp": 20, "condition": "Unknown", "humidity": 50})


@tool
def search_flights(from_city: str, to_city: str, date: str) -> list:
    """Search for flights between cities.

    Args:
        from_city: Departure city
        to_city: Destination city
        date: Travel date (YYYY-MM-DD)

    Returns:
        List of flight options with price and duration
    """
    # Mock implementation
    if from_city == "New York" and to_city == "London":
        return [
            {"airline": "BA", "price": 450, "duration": "7h"},
            {"airline": "AA", "price": 520, "duration": "7.5h"},
        ]
    return [{"airline": "Generic Air", "price": 300, "duration": "5h"}]


@tool
def calculate_trip_cost(flight_price: float, hotel_nights: int, daily_food: float = 50) -> dict:
    """Calculate total trip cost.

    Args:
        flight_price: Round-trip flight cost
        hotel_nights: Number of hotel nights
        daily_food: Daily food budget (default $50)

    Returns:
        Dict with breakdown of costs
    """
    hotel_rate = 120  # per night
    total = flight_price + (hotel_nights * hotel_rate) + (hotel_nights * daily_food)

    return {
        "flight": flight_price,
        "hotel": hotel_nights * hotel_rate,
        "food": hotel_nights * daily_food,
        "total": total,
        "breakdown": f"Flight: ${flight_price}, Hotel: ${hotel_nights * hotel_rate} ({hotel_nights} nights × ${hotel_rate}), Food: ${hotel_nights * daily_food} ({hotel_nights} days × ${daily_food})",
    }


def main():
    agent = ReactAgent(
        tools=[get_weather, search_flights, calculate_trip_cost],
        model="gpt-4o-mini",  # or any OpenRouter model
    )

    print("ReactAgent Demo - Enhanced Features")
    print("=" * 50)

    # Example 1: Weather comparison with scratchpad thinking
    print("\n1. Weather comparison:")
    answer = agent.run(
        "Compare the weather in Tokyo and London. Which city has better conditions for outdoor activities?",
        max_steps=10,
        verbose=True,
    )
    print(f"Answer: {answer}")

    # Example 2: Trip planning with multiple tools
    print("\n2. Trip planning:")
    answer = agent.run(
        "I want to fly from New York to London for 3 nights. What's the weather like there and how much will the trip cost if I take the cheapest flight?",
        max_steps=10,
        verbose=True,
    )
    print(f"Answer: {answer}")

    # Example 3: Error recovery - intentionally trigger argument error
    print("\n3. Demonstrating error recovery:")
    answer = agent.run(
        "Calculate the cost of a trip with a $500 flight for 5 nights", max_steps=10, verbose=True
    )
    print(f"Answer: {answer}")


if __name__ == "__main__":
    main()
