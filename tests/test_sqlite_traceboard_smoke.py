import pytest
import os
import sqlite3
import time
import subprocess
import requests
import sys
import logging
from pathlib import Path
from typing import Generator, Tuple

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

# DB Path defined within the fixture now
TRACEBOARD_HOST = "127.0.0.1" 
TRACEBOARD_PORT = 8009 
TRACEBOARD_URL = f"http://{TRACEBOARD_HOST}:{TRACEBOARD_PORT}"
TRACEBOARD_SCRIPT_PATH = project_root / "src/tinyagent/observability/traceboard.py"

@pytest.fixture(scope="module")
def traceboard_setup() -> Generator[Tuple[str, subprocess.Popen], None, None]:
    """Fixture to set up tracer, start the traceboard server, capture its process, and clean up."""
    # --- OTel imports needed here ---
    from opentelemetry import trace
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from tinyagent.observability.sqlite_exporter import SQLiteSpanExporter
    # --- Need configure_tracing ---
    from tinyagent.observability.tracer import configure_tracing, _tracer_provider # Import necessary items
    # --- End OTel imports ---
    
    db_path = Path(__file__).parent / "test_traceboard_traces.db"
    print(f"--- Using Test DB Path: {db_path.absolute()} ---")

    # 1. Cleanup old DB if exists
    print(f"--- Cleaning up old test DB (if exists): {db_path} ---")
    db_path.unlink(missing_ok=True)
    
    # 2. FORCE configure tracing specifically for this test
    print("--- Forcibly configuring TracerProvider for test with SQLite Exporter ---")
    test_tracing_config = {
        'observability': {
            'tracing': {
                'enabled': True,
                'service_name': 'test_traceboard_smoke', # Unique service name for test
                'sampling_rate': 1.0,
                'exporter': {
                    'type': 'sqlite',
                    'db_path': str(db_path.absolute())
                },
                 'attributes': { # Optional: add test-specific resource attributes
                     'test.run_id': str(time.time())
                 }
            }
        }
    }
    configure_tracing(config=test_tracing_config, force=True)
    print("--- Test TracerProvider configured ---")

    # 3. Start traceboard server as a subprocess
    traceboard_proc = None
    try:
        # ... (rest of server startup logic is correct)
        python_executable = sys.executable
        env = os.environ.copy()
        env['PYTHONPATH'] = str(project_root / 'src') + os.pathsep + env.get('PYTHONPATH', '')
        # Ensure PYTHONUNBUFFERED is set to see logs immediately
        env['PYTHONUNBUFFERED'] = "1" 
        print(f"\nStarting traceboard server: {python_executable} {TRACEBOARD_SCRIPT_PATH} --host {TRACEBOARD_HOST} --port {TRACEBOARD_PORT} --db {db_path.absolute()}")
        traceboard_proc = subprocess.Popen(
            [
                python_executable, 
                str(TRACEBOARD_SCRIPT_PATH), 
                "--host", TRACEBOARD_HOST, 
                "--port", str(TRACEBOARD_PORT),
                "--db", str(db_path.absolute())
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True, # Decode stdout/stderr as text
            env=env
        )
        max_wait = 30
        start_time = time.time()
        server_ready = False
        while time.time() - start_time < max_wait:
            if traceboard_proc.poll() is not None: # Check if server process died
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
                    print("Traceboard server started successfully.")
                    server_ready = True
                    break
            except requests.ConnectionError:
                time.sleep(0.5)
            except Exception as e:
                print(f"Error checking traceboard server status endpoint: {e}")
                # Optionally read/print stdout/stderr here too if check fails
                time.sleep(0.5) # Give logs a moment
                # Note: communicate() waits for process end, use non-blocking read?
                # For simplicity, we'll rely on the final check or test failure printout
                break # Stop checking if status check throws other errors

        if not server_ready:
            # Server didn't become ready, try to get logs before raising error
            stdout, stderr = ("", "")
            try:
                 stdout, stderr = traceboard_proc.communicate(timeout=1) # Read remaining output
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

        # 4. Yield the DB path AND the process object to the test
        yield str(db_path.absolute()), traceboard_proc # MODIFIED yield

    finally:
        # 5. Teardown: Terminate server, shutdown provider, remove DB
        print("\n--- Test Teardown --- ")
        if traceboard_proc:
            print("Terminating traceboard server...")
            traceboard_proc.terminate()
            try:
                traceboard_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Traceboard server did not terminate gracefully, killing.")
                traceboard_proc.kill()
            print("Traceboard server terminated.")
            
        # Shutdown the TracerProvider (optional but good practice)
        print("Shutting down global TracerProvider...")
        # Note: Shutting down the provider might affect other tests if run in sequence
        # without proper isolation or re-configuration. 
        current_provider = trace.get_tracer_provider()
        if hasattr(current_provider, 'shutdown'):
             current_provider.shutdown()
             print("Global TracerProvider shut down.")
        else:
            print("Global TracerProvider does not support shutdown.")
        
        # Remove DB file 
        if db_path.exists():
            print(f"Removing test database: {db_path}")
            try:
                db_path.unlink()
            except OSError as e:
                 print(f"Warning: Could not remove test DB {db_path}: {e}")
        else:
            print(f"Test database already removed or never created: {db_path}")

# --- Test Tool ---

@tool
def simple_math_test(a: int, b: int) -> int:
    """A simple function to be traced."""
    print(f"Executing simple_math_test({a}, {b})")
    result = a + b
    print(f"Result: {result}")
    return result

# --- Test Case ---

def test_sqlite_export_and_traceboard_access(traceboard_setup):
    """
    Runs an agent, checks SQLite DB, and accesses the traceboard via HTTP.
    Prints server logs if HTTP access fails.
    """
    # --- OTel import needed here for force_flush ---
    from opentelemetry import trace 
    # --- End OTel import ---
    
    # Unpack fixture results
    db_path, traceboard_proc = traceboard_setup # MODIFIED unpack

    # 1. Run the agent to generate a trace
    # Use a minimal config for the agent itself
    agent_config = load_config() 
    agent = tiny_agent(tools=[simple_math_test], 
                      model=agent_config.get('model', {}).get('default'),
                      trace_this_agent=True) # Explicitly enable tracing for this test agent
    try:
        agent.run("Use simple_math_test to add 55 and 45")
    except Exception as e:
        pytest.fail(f"Agent run failed unexpectedly: {e}")

    # Explicitly flush the provider before checking the DB
    print("--- Forcing TracerProvider flush ---")
    trace.get_tracer_provider().force_flush()
    print("--- Flush complete --- ")
    time.sleep(2.0) # INCREASED sleep after flush

    # 2. Verify DB file exists and has data
    assert os.path.exists(db_path), f"SQLite database file not found at {db_path}"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM spans")
    span_count = cursor.fetchone()[0]
    tool_span_count = 0
    try:
        cursor.execute("SELECT COUNT(*) FROM spans WHERE name LIKE ?", ('tool.execute.%',))
        tool_span_count = cursor.fetchone()[0]
    except sqlite3.OperationalError as e:
        logging.warning(f"Could not query tool spans (maybe old schema?): {e}")
    conn.close()
    print(f"Found {span_count} total spans, {tool_span_count} tool spans in the database.")
    assert span_count >= 2, f"Expected at least 2 spans (agent.run + tool), found {span_count}"
    assert tool_span_count > 0, "No tool execution spans were recorded."
    
    # Find the specific span we expect
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT trace_id, span_id, name FROM spans WHERE name = ?", ("agent.run",))
    agent_span = cursor.fetchone()
    conn.close()
    assert agent_span is not None, "Did not find the 'agent.run' span in the DB."
    trace_id = agent_span[0]
    span_name = agent_span[2]
    print(f"Found trace {trace_id} with span '{span_name}'")


    # 3. Access Traceboard via HTTP
    # Check root page
    try:
        response_root = requests.get(TRACEBOARD_URL + "/", timeout=5)
        response_root.raise_for_status() # Raise exception for bad status codes

        # Restore original HTML Assertions
        assert "TinyAgent Traceboard" in response_root.text, "Root page content mismatch."
        assert trace_id in response_root.text, "Trace ID not found on root page."
        
        print("Successfully accessed traceboard root page and verified HTML content.") # Restore print message

    except requests.RequestException as e:
        # ADDED: Print server logs on failure
        print("\n--- Traceboard Access Failed! ---")
        print(f"Error: {e}")
        # Attempt to read any remaining output from the server process
        stdout, stderr = ("", "")
        if traceboard_proc and traceboard_proc.poll() is None: # Check if proc still running
             # Careful: communicate() waits. If server hangs, this hangs.
             # A non-blocking read might be better in complex scenarios.
             # For now, assume short logs or quick termination after error.
             try:
                  stdout, stderr = traceboard_proc.communicate(timeout=2)
             except subprocess.TimeoutExpired:
                  print("Timed out reading traceboard logs after failure.")
                  # Maybe try reading stdout/stderr attributes directly if available?
                  stdout = traceboard_proc.stdout.read() if traceboard_proc.stdout else ""
                  stderr = traceboard_proc.stderr.read() if traceboard_proc.stderr else ""
        elif traceboard_proc:
            stdout = traceboard_proc.stdout.read() if traceboard_proc.stdout else ""
            stderr = traceboard_proc.stderr.read() if traceboard_proc.stderr else ""

        print("--- Traceboard stdout (after failure) ---")
        print(stdout)
        print("--- Traceboard stderr (after failure) ---")
        print(stderr)
        print("--------------------------------------")
        pytest.fail(f"Failed to access traceboard root page: {e}")

    # Check trace detail page (only if root page succeeded)
    # --- RE-ENABLE --- 
    try:
        trace_detail_url = f"{TRACEBOARD_URL}/trace/{trace_id}"
        response_detail = requests.get(trace_detail_url, timeout=5)
        response_detail.raise_for_status()
        # Keep original HTML check for detail page title
        assert f"Trace Detail - {trace_id}" in response_detail.text, "Trace detail page title mismatch."
        assert span_name in response_detail.text, f"Span name '{span_name}' not found on detail page."
        print(f"Successfully accessed trace detail page for {trace_id}.")
    except requests.RequestException as e:
        # ... (existing error logging) ...
        pytest.fail(f"Failed to access traceboard detail page: {e}")
        
    # --- ADDED PAUSE --- 
    print("\n--- Test checks complete. Pausing for 30 seconds with periodic checks. --- ")
    print(f"Access traceboard at: {TRACEBOARD_URL}")
    # time.sleep(30) # Replace simple sleep with active checking loop
    for i in range(6): # Check ~every 5 seconds for 30 seconds
        print(f"\n--- Checking server during pause (Iteration {i+1}/6) ---")
        try:
            response_check = requests.get(TRACEBOARD_URL + "/", timeout=3)
            print(f"Status Code: {response_check.status_code}")
            if response_check.status_code == 200:
                if trace_id in response_check.text:
                    print(f"Trace ID {trace_id} FOUND in response.")
                else:
                    print(f"Trace ID {trace_id} NOT FOUND in response.")
                    # Optional: print first few lines of response text
                    # print("Response text snippet:")
                    # print(response_check.text[:200]) 
            else:
                print("Server returned non-200 status.")
        except requests.RequestException as e:
            print(f"Error accessing server during pause: {e}")
        
        if i < 5: # Don't sleep after the last iteration
            time.sleep(5)
            
    print("--- Pause finished. Test completing. ---") 