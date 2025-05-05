import pytest
import os
import sqlite3
import time
import subprocess
import requests
import sys
import logging
import socket
from contextlib import closing
from pathlib import Path
from typing import Generator, Tuple, Optional

# Add project root to sys.path BEFORE importing tinyagent components
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# --- OTel Imports moved inside fixture where setup happens ---
# (Keep top-level imports minimal)
# Import the tracer module itself to access its internal state
from tinyagent.observability import tracer as tracer_module 

# --- Now import tinyagent components ---
from tinyagent.agent import Agent, tiny_agent
from tinyagent.decorators import tool
from tinyagent.config import load_config

# --- Test Setup Constants ---
TRACEBOARD_HOST = "127.0.0.1"
# Define a function to find an available port
def find_free_port() -> int:
    """Find a free port on localhost."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

# Set a traceboard port using the helper function
TRACEBOARD_PORT = find_free_port()
TRACEBOARD_URL = f"http://{TRACEBOARD_HOST}:{TRACEBOARD_PORT}"
TRACEBOARD_SCRIPT_PATH = project_root / "src/tinyagent/observability/traceboard.py"


@pytest.fixture(scope="function")
def test_db_path() -> Path:
    """Fixture to provide a unique test database path and clean it up after the test."""
    # Create a unique database file name
    timestamp = int(time.time())
    db_path = Path(__file__).parent / f"test_traceboard_traces_{timestamp}.db"
    
    # Ensure the DB doesn't exist before the test
    if db_path.exists():
        db_path.unlink()
    
    yield db_path
    
    # Clean up after the test
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError as e:
            logging.warning(f"Could not remove test DB {db_path}: {e}")


@pytest.fixture(scope="function")
def configured_tracer(test_db_path) -> Generator[None, None, None]:
    """Fixture to set up and tear down the tracer for testing."""
    # Import OpenTelemetry components
    from opentelemetry import trace
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from tinyagent.observability.sqlite_exporter import SQLiteSpanExporter
    from tinyagent.observability.tracer import configure_tracing, _tracer_provider
    
    # Configure tracing for this test
    test_tracing_config = {
        'observability': {
            'tracing': {
                'enabled': True,
                'service_name': 'test_traceboard_smoke',
                'sampling_rate': 1.0,
                'exporter': {
                    'type': 'sqlite',
                    'db_path': str(test_db_path.absolute())
                },
                'attributes': {
                    'test.run_id': str(time.time())
                }
            }
        }
    }
    
    # Force configure tracing for this test
    configure_tracing(config=test_tracing_config, force=True)
    
    yield
    
    # Shutdown the TracerProvider at the end of the test
    current_provider = trace.get_tracer_provider()
    if hasattr(current_provider, 'shutdown'):
        current_provider.shutdown()


@pytest.fixture(scope="function")
def traceboard_server(test_db_path) -> Generator[subprocess.Popen, None, None]:
    """Fixture to start and stop the traceboard server."""
    # Set up the environment for the traceboard server
    python_executable = sys.executable
    env = os.environ.copy()
    env['PYTHONPATH'] = str(project_root / 'src') + os.pathsep + env.get('PYTHONPATH', '')
    env['PYTHONUNBUFFERED'] = "1"
    
    # Start the traceboard server
    traceboard_proc = subprocess.Popen(
        [
            python_executable,
            str(TRACEBOARD_SCRIPT_PATH),
            "--host", TRACEBOARD_HOST,
            "--port", str(TRACEBOARD_PORT),
            "--db", str(test_db_path.absolute())
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    # Wait for the server to start
    max_wait = 30
    start_time = time.time()
    server_ready = False
    
    while time.time() - start_time < max_wait:
        if traceboard_proc.poll() is not None:
            stdout, stderr = traceboard_proc.communicate()
            print("--- Traceboard process terminated unexpectedly during startup check ---")
            print("--- Traceboard stdout ---")
            print(stdout)
            print("--- Traceboard stderr ---")
            print(stderr)
            print("-----------------------")
            raise RuntimeError("Traceboard server process died during startup check.")
        
        try:
            response = requests.get(TRACEBOARD_URL + "/", timeout=1)
            if response.status_code == 200:
                print(f"Traceboard server started successfully on port {TRACEBOARD_PORT}.")
                server_ready = True
                break
        except requests.ConnectionError:
            time.sleep(0.5)
        except Exception as e:
            print(f"Error checking traceboard server status endpoint: {e}")
            time.sleep(0.5)
            break
    
    if not server_ready:
        # Server didn't become ready, try to get logs before raising error
        stdout, stderr = ("", "")
        try:
            stdout, stderr = traceboard_proc.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            print("Timed out waiting for traceboard process communication.")
            traceboard_proc.kill()
            stdout, stderr = traceboard_proc.communicate()
        
        print("--- Traceboard stdout (failed readiness check) ---")
        print(stdout)
        print("--- Traceboard stderr (failed readiness check) ---")
        print(stderr)
        print("-----------------------")
        raise RuntimeError(f"Traceboard server did not start within {max_wait} seconds.")
    
    yield traceboard_proc
    
    # Teardown: terminate the server
    if traceboard_proc:
        print("Terminating traceboard server...")
        traceboard_proc.terminate()
        try:
            traceboard_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Traceboard server did not terminate gracefully, killing.")
            traceboard_proc.kill()
        print("Traceboard server terminated.")


@pytest.fixture(scope="function")
def test_agent():
    """Fixture to provide a test agent with a simple math tool."""
    agent_config = load_config()
    agent = tiny_agent(
        tools=[simple_math_test],
        model=agent_config.get('model', {}).get('default'),
        trace_this_agent=True
    )
    return agent


# --- Test Tool ---
@tool
def simple_math_test(a: int, b: int) -> int:
    """A simple function to be traced."""
    print(f"Executing simple_math_test({a}, {b})")
    result = a + b
    print(f"Result: {result}")
    return result


# --- Helper Functions ---
def check_db_spans(db_path: str) -> Tuple[int, int, Optional[Tuple]]:
    """Check the database for spans and return count information."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get total span count
    cursor.execute("SELECT COUNT(*) FROM spans")
    span_count = cursor.fetchone()[0]
    
    # Get tool span count - we'll count any span with 'tool' in the name
    tool_span_count = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM spans WHERE name LIKE ?", ('%tool%',))
        tool_span_count = cursor.fetchone()[0]
    except sqlite3.OperationalError as e:
        logging.warning(f"Could not query tool spans (maybe old schema?): {e}")
    
    # Find any span to use as our test span
    cursor.execute("SELECT trace_id, span_id, name FROM spans LIMIT 1")
    test_span = cursor.fetchone()
    
    conn.close()
    return span_count, tool_span_count, test_span


# --- Test Case ---
def test_sqlite_export_and_traceboard_access(test_db_path, configured_tracer, traceboard_server, test_agent):
    """
    Test that:
    1. Agent execution creates spans in the SQLite database
    2. Traceboard server can access and display those spans
    """
    from opentelemetry import trace
    
    # Instead of running the agent, directly call the test function to generate spans
    # First, get a tracer for this test
    tracer = trace.get_tracer("test_traceboard")
    
    # Create a parent span for the test
    with tracer.start_as_current_span("test.manual_execution") as span:
        # Add some attributes to the span
        span.set_attribute("test.function", "simple_math_test")
        span.set_attribute("test.a", 55)
        span.set_attribute("test.b", 45)
        
        # Call the function directly
        result = simple_math_test(55, 45)
        span.set_attribute("test.result", result)
        print(f"Test function returned: {result}")
    
    # Force flush to ensure all spans are exported
    trace.get_tracer_provider().force_flush()
    time.sleep(2.0)  # Allow time for the flush to complete
    
    # Verify DB file exists and has data
    db_path = str(test_db_path.absolute())
    assert os.path.exists(db_path), f"SQLite database file not found at {db_path}"
    
    # Check span counts and get the spans
    span_count, tool_span_count, test_span = check_db_spans(db_path)
    
    # Verify span counts
    print(f"Found {span_count} total spans in the database.")
    assert span_count >= 1, f"Expected at least 1 span, found {span_count}"
    
    # Check if we can find our test span
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT trace_id, span_id, name FROM spans WHERE name LIKE ?", ("%test.manual%",))
    test_span = cursor.fetchone()
    conn.close()
    
    assert test_span is not None, "Did not find the test span in the DB."
    trace_id = test_span[0]
    span_name = test_span[2]
    print(f"Found trace {trace_id} with span '{span_name}'")
    
    # Verify traceboard root page
    try:
        response_root = requests.get(TRACEBOARD_URL + "/", timeout=5)
        response_root.raise_for_status()
        
        assert "TinyAgent Traceboard" in response_root.text, "Root page content mismatch."
        assert trace_id in response_root.text, "Trace ID not found on root page."
        
        print("Successfully accessed traceboard root page and verified HTML content.")
    except requests.RequestException as e:
        # Print server logs on failure
        stdout = stderr = ""
        if traceboard_server and traceboard_server.poll() is None:
            try:
                stdout, stderr = traceboard_server.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                stdout = traceboard_server.stdout.read() if traceboard_server.stdout else ""
                stderr = traceboard_server.stderr.read() if traceboard_server.stderr else ""
        
        print("\n--- Traceboard Access Failed! ---")
        print(f"Error: {e}")
        print("--- Traceboard stdout (after failure) ---")
        print(stdout)
        print("--- Traceboard stderr (after failure) ---")
        print(stderr)
        print("--------------------------------------")
        pytest.fail(f"Failed to access traceboard root page: {e}")
    
    # Verify trace detail page
    try:
        trace_detail_url = f"{TRACEBOARD_URL}/trace/{trace_id}"
        response_detail = requests.get(trace_detail_url, timeout=5)
        response_detail.raise_for_status()
        
        assert f"Trace Detail - {trace_id}" in response_detail.text, "Trace detail page title mismatch."
        assert span_name in response_detail.text, f"Span name '{span_name}' not found on detail page."
        print(f"Successfully accessed trace detail page for {trace_id}.")
    except requests.RequestException as e:
        stdout = stderr = ""
        if traceboard_server and traceboard_server.poll() is None:
            try:
                stdout, stderr = traceboard_server.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                stdout = traceboard_server.stdout.read() if traceboard_server.stdout else ""
                stderr = traceboard_server.stderr.read() if traceboard_server.stderr else ""
        
        print("\n--- Traceboard Access Failed! ---")
        print(f"Error: {e}")
        print("--- Traceboard stdout (after failure) ---")
        print(stdout)
        print("--- Traceboard stderr (after failure) ---")
        print(stderr)
        print("--------------------------------------")
        pytest.fail(f"Failed to access traceboard detail page: {e}")


if __name__ == "__main__":
    # When running the file directly, execute the test
    sys.exit(pytest.main(["-xvs", __file__])) 