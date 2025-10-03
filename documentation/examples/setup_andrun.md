# TinyAgent-OS Demo Guide

A complete example demonstrating ReactAgent capabilities with scratchpad thinking, error recovery, and tool usage.

## Setup

1. **Create virtual environment:**

   ```bash
   uv venv
   source .venv/bin/activate
   ```

2. **Install package:**

   ```bash
   uv pip install tiny-agent-os
   ```

3. **Configure environment (.env):**
   ```env
   OPENAI_API_KEY=sk-or-v1-your-api-key
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   ```

## Demo Code

```python
"""
ReactAgent Demo - Showcasing scratchpad, error recovery, and observations
"""

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from tinyagent import ReactAgent, tool


@tool
def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    weather_data = {
        "Tokyo": {"temp": 22, "condition": "Partly cloudy", "humidity": 65},
        "New York": {"temp": 18, "condition": "Sunny", "humidity": 45},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 80},
    }
    return weather_data.get(city, {"temp": 20, "condition": "Unknown", "humidity": 50})


@tool
def calculate_trip_cost(flight_price: float, hotel_nights: int, daily_food: float = 50) -> dict:
    """Calculate total trip cost."""
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
        tools=[get_weather, calculate_trip_cost],
        model="z-ai/glm-4.6",
    )

    print("ReactAgent Demo")
    print("=" * 30)

    # Example 1: Weather comparison
    print("\n1. Weather comparison:")
    answer = agent.run(
        "Compare the weather in Tokyo and London. Which city has better conditions for outdoor activities?",
        max_steps=10,
        verbose=True,
    )
    print(f"Answer: {answer}")

    # Example 2: Cost calculation
    print("\n2. Trip cost calculation:")
    answer = agent.run(
        "Calculate the cost of a trip with a $500 flight for 5 nights",
        max_steps=10,
        verbose=True,
    )
    print(f"Answer: {answer}")


if __name__ == "__main__":
    main()
```

## Key Features Demonstrated

1. **Scratchpad Thinking**: Agent shows step-by-step reasoning
2. **Tool Integration**: Seamless use of custom tools
3. **Error Recovery**: Handles missing information gracefully
4. **Verbose Output**: Detailed process visibility
5. **Cost Analysis**: Complex calculations with breakdowns

## Run the Demo

```bash
source .venv/bin/activate
python demo.py
```

## Expected Output

The demo will show:

- Detailed agent reasoning process
- Tool calls and results
- Final comprehensive answers
- Step-by-step execution with verbose logging

## Model Configuration

Uses OpenRouter with GLM-4.6 model. Update the model parameter as needed:

- `gpt-4o-mini`
- `z-ai/glm-4.6`
- Other OpenRouter models

This example showcases the production-ready capabilities of TinyAgent-OS for building intelligent LLM-powered agents.
