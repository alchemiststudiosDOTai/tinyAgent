#!/usr/bin/env python3
"""
Test runner for the Agent Character Test Suite.

This script provides a convenient way to run all character tests
with proper configuration and reporting.
"""

import os
import sys
import subprocess
import pathlib
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))


def check_environment() -> bool:
    """Check if required environment variables are set."""
    required_vars = ["OPENROUTER_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables before running tests.")
        return False
    
    print("✅ Environment variables configured")
    return True


def check_config() -> bool:
    """Check if configuration files exist."""
    config_path = pathlib.Path(__file__).parent.parent.parent / "config.yml"
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("Please create config.yml with base_url configured.")
        return False
    
    print("✅ Configuration file found")
    return True


def run_pytest(args: List[str]) -> int:
    """Run pytest with the given arguments."""
    base_args = [
        sys.executable, "-m", "pytest",
        str(pathlib.Path(__file__).parent),
        "-v",
        "--tb=short",
        "--durations=10",
    ]
    
    cmd = base_args + args
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)
    
    return subprocess.call(cmd)


def main():
    """Main test runner function."""
    print("🧪 Agent Character Test Suite Runner")
    print("=" * 60)
    
    # Check prerequisites
    if not check_environment():
        return 1
    
    if not check_config():
        return 1
    
    # Parse command line arguments
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Add some helpful default options if none specified
    if not args:
        print("Running all character tests with default options...")
        args = ["--maxfail=5"]  # Stop after 5 failures
    
    # Special command handling
    if "help" in args or "--help" in args or "-h" in args:
        print("""
Usage: python run_tests.py [pytest-args]

Examples:
  python run_tests.py                          # Run all tests
  python run_tests.py --maxfail=1             # Stop on first failure
  python run_tests.py -k "unicode"            # Run only unicode tests
  python run_tests.py --cov=tinyagent.agent   # Run with coverage
  python run_tests.py -x                      # Stop on first failure (short)
  python run_tests.py -v                      # Verbose output
  python run_tests.py --tb=long               # Long traceback format
  
Test Categories:
  -k "character"     # Basic character handling tests
  -k "parsing"       # JSON parsing edge cases  
  -k "retry"         # Retry mechanism tests
  -k "config"        # Configuration tests
  -k "unicode"       # Unicode-specific tests
  -k "edge"          # Edge case tests
  -k "memory"        # Memory/performance tests
        """)
        return 0
    
    if "fast" in args:
        args.remove("fast")
        args.extend(["-x", "--maxfail=1"])
        print("🚀 Fast mode: stopping on first failure")
    
    if "coverage" in args:
        args.remove("coverage")
        args.extend([
            "--cov=tinyagent.agent",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
        print("📊 Running with coverage reporting")
    
    # Run the tests
    try:
        return_code = run_pytest(args)
        
        print("-" * 60)
        if return_code == 0:
            print("✅ All tests passed!")
        else:
            print(f"❌ Tests failed with return code: {return_code}")
        
        return return_code
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())