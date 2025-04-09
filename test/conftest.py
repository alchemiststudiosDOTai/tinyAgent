"""
Pytest configuration file for tinyAgent tests.
"""
import os
import sys

# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# We don't need to import the core components directly
# as we're running the cookbook examples as separate processes 