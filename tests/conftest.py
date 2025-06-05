"""
Pytest configuration and fixtures for tinyAgent tests.
"""

import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Configure logging to show INFO level and above
def pytest_configure(config):
    """Configure pytest to show logs during test execution."""
    # Set up basic logging configuration with debug level by default
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG to see all messages
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    # Enable debug logging for tinyagent
    logging.getLogger("tinyagent").setLevel(logging.DEBUG)

    # Disable logging for specific noisy loggers if needed
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
