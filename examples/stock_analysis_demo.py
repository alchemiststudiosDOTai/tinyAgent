#!/usr/bin/env python3
"""
Stock Analysis Demo - tinyAgent in Action

This demo shows how tinyAgent combines ReactAgent and TinyCodeAgent
to research stocks, analyze data, and generate investment insights.

Perfect example of real-world AI agent usage.
"""

import asyncio

from dotenv import load_dotenv

from tinyagent import (
    ReactAgent,
    TinyCodeAgent,
    TrustLevel,
    tool,
)

load_dotenv()

# =============================================================================
# TOOLS
# =============================================================================


@tool
def web_search(query: str, max_results: int = 3) -> str:
    """Search for stock market information (mock implementation).

    Args:
        query: Search query
        max_results: Maximum results to return

    Returns:
        Formatted search results
    """
    # Mock results for demo
    return f"""
    Search results for "{query}":
    1. Recent {query} Analysis - Bullish trend expected despite volatility
    2. Market Report - {query} beats earnings, technical indicators positive
    3. Investment Outlook - Strong fundamentals, moderate risk level
    """


@tool
def calculate_returns(prices: list[float]) -> list[float]:
    """Calculate daily returns from price data.

    Args:
        prices: List of closing prices

    Returns:
        Daily percentage returns
    """
    returns = []
    for i in range(1, len(prices)):
        daily_return = ((prices[i] - prices[i - 1]) / prices[i - 1]) * 100
        returns.append(round(daily_return, 2))
    return returns


@tool
def volatility(returns: list[float]) -> float:
    """Calculate annualized volatility.

    Args:
        returns: List of daily returns

    Returns:
        Annualized volatility percentage
    """
    import math

    if len(returns) < 2:
        return 0.0

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std_dev = math.sqrt(variance)
    annualized = std_dev * math.sqrt(252)
    return round(annualized, 2)


# =============================================================================
# MAIN DEMO
# =============================================================================


async def stock_analysis_pipeline():
    """Complete stock analysis using both agents."""

    print("🤖 tinyAgent Stock Analysis Demo")
    print("=" * 50)

    # Step 1: ReactAgent research
    print("\n📊 Step 1: Market Research (ReactAgent)")
    researcher = ReactAgent(tools=[web_search])

    research = await researcher.run("Research AAPL stock performance and market outlook")
    print(f"Research: {research}")

    # Step 2: TinyCodeAgent analysis
    print("\n📈 Step 2: Technical Analysis (TinyCodeAgent)")

    analyst = TinyCodeAgent(
        tools=[calculate_returns, volatility],
        trust_level=TrustLevel.LOCAL,
        extra_imports=["math", "statistics"],
    )

    analysis_task = """
    Analyze this stock data using Python:

    AAPL prices: [150, 155, 152, 160, 158, 165, 168, 162, 170, 175]

    Tasks:
    1. Calculate daily returns
    2. Compute volatility
    3. Find average return and best/worst days
    4. Calculate total gain over period
    5. Based on research and analysis, provide investment recommendation

    Write Python code to complete this analysis.
    """

    result = await analyst.run(analysis_task)
    print("\n📋 Analysis Result:")
    print(result)


async def main():
    """Run the stock analysis demo."""
    try:
        await stock_analysis_pipeline()
        print("\n✅ Stock analysis completed!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
