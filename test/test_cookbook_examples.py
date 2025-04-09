import subprocess
import glob
import os
import pathlib
import sys

import pytest

COOKBOOK_DIR = pathlib.Path(__file__).parent.parent / "cookbook"
EXPECTED_DIR = COOKBOOK_DIR / "expected"

# Ensure expected directory exists
EXPECTED_DIR.mkdir(parents=True, exist_ok=True)

# We don't need to import the package directly for these tests
# as we're running the cookbook examples as separate processes

example_scripts = sorted(COOKBOOK_DIR.glob("*.py"))

@pytest.mark.parametrize("script_path", example_scripts)
def test_cookbook_example(script_path):
    """Run cookbook example, capture output, compare or bootstrap expected output."""
    # Run the script as a module to ensure imports work correctly
    module_path = f"cookbook.{script_path.stem}"
    
    # Use python -m to run the module
    result = subprocess.run(
        [sys.executable, "-m", module_path],
        capture_output=True,
        text=True,
        timeout=120,  # prevent hanging scripts
        cwd=str(COOKBOOK_DIR.parent)  # Set working directory to project root
    )

    # Fail if script errors
    assert result.returncode == 0, (
        f"Script {script_path.name} exited with code {result.returncode}\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    expected_file = EXPECTED_DIR / (script_path.stem + ".txt")

    if not expected_file.exists():
        # Bootstrap mode: save current output as expected
        with open(expected_file, "w", encoding="utf-8") as f:
            f.write(result.stdout)
        # Pass the test and inform user
        print(f"[BOOTSTRAP] Saved baseline expected output for {script_path.name}")
    else:
        with open(expected_file, "r", encoding="utf-8") as f:
            expected_output = f.read()
        # Compare outputs
        assert result.stdout == expected_output, (
            f"Output mismatch for {script_path.name}\n"
            f"--- Expected ---\n{expected_output}\n"
            f"--- Got ---\n{result.stdout}"
        )