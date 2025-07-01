"""
TinyCodeAgent Demo - Python-executing ReAct agent

This example demonstrates:
1. Mathematical computations
2. Data analysis with tools
3. Algorithm implementation
"""

from tinyagent import TinyCodeAgent, tool


@tool
def fetch_stock_data(symbol: str) -> dict:
    """Fetch stock market data for a symbol.

    Returns dict with keys:
    - price: float (current price)
    - change: float (daily change percentage)
    - volume: int (trading volume)
    - high: float (daily high)
    - low: float (daily low)
    """
    # Mock data
    stocks = {
        "AAPL": {"price": 195.89, "change": 1.2, "volume": 48293847, "high": 196.38, "low": 194.02},
        "GOOGL": {
            "price": 178.23,
            "change": -0.5,
            "volume": 23847562,
            "high": 179.99,
            "low": 177.30,
        },
        "MSFT": {"price": 429.71, "change": 0.8, "volume": 18937465, "high": 431.00, "low": 427.55},
    }
    return stocks.get(
        symbol, {"price": 100.0, "change": 0.0, "volume": 1000000, "high": 101.0, "low": 99.0}
    )


@tool
def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Get exchange rate between currencies.

    Args:
        from_currency: Source currency (e.g., 'USD')
        to_currency: Target currency (e.g., 'EUR')

    Returns:
        float: Exchange rate
    """
    # Mock rates (USD as base)
    rates = {
        ("USD", "EUR"): 0.92,
        ("USD", "GBP"): 0.79,
        ("EUR", "USD"): 1.09,
        ("GBP", "USD"): 1.27,
        ("EUR", "GBP"): 0.86,
        ("GBP", "EUR"): 1.16,
    }
    return rates.get((from_currency, to_currency), 1.0)


def main():
    agent = TinyCodeAgent(
        tools=[fetch_stock_data, get_exchange_rate],
        model="gpt-4o-mini",  # or "anthropic/claude-3.5-haiku", etc.
        extra_imports=["math"],
    )

    print("TinyCodeAgent Demo")
    print("=" * 50)

    # Example 1: Mathematical computation
    print("\n1. Fibonacci sequence:")
    answer = agent.run("Calculate the first 10 Fibonacci numbers and find their sum", verbose=True)
    print(f"Answer: {answer}")

    # Example 2: Stock portfolio analysis
    print("\n2. Portfolio analysis:")
    answer = agent.run(
        "I have 10 shares of AAPL and 5 shares of MSFT. What's my portfolio value and which stock has better daily performance?",
        verbose=True,
    )
    print(f"Answer: {answer}")

    # Example 3: Currency conversion with calculations
    print("\n3. International investment:")
    answer = agent.run(
        "If I invest $10,000 in European stocks and get 15% returns in EUR, how much will I have in USD? Use current exchange rates.",
        verbose=True,
    )
    print(f"Answer: {answer}")


if __name__ == "__main__":
    main()
