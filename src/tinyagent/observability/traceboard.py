import argparse  # Use argparse for configuration
import json
import logging
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

# Determine the base directory for templates relative to this file
# Assuming templates will be in src/tinyagent/observability/templates
TEMPLATE_DIR = Path(__file__).parent / "templates"

app = FastAPI(
    title="TinyAgent Traceboard",
    description="A simple local dashboard to view OpenTelemetry traces stored in SQLite.",
    version="0.1.0",
)
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# --- Database Connection --- #


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Establishes a connection to the specified SQLite database path."""
    # Connect to the provided path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dictionary-like objects
    return conn


# --- Routes --- #

# Store parsed args globally for routes to access (simpler than passing Request state)
# This is generally okay for a simple tool like this, but consider dependency injection for complex apps.
parsed_args = None


@app.on_event("startup")
async def startup_event():
    """Parse CLI args on startup to make db path available to routes."""
    global parsed_args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db", type=str, default="traces.db", help="Path to SQLite database file."
    )
    # Add host/port if needed elsewhere, otherwise they are only used by uvicorn
    # Only parse known args to avoid conflicts with uvicorn internal args
    parsed_args, _ = parser.parse_known_args()
    print(f"--- Traceboard using database (on startup): {parsed_args.db} ---")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Display the main traceboard page with a list of recent traces."""
    logger.info("--- Handling request for / ---")
    if not parsed_args:
        logger.error("Server configuration (parsed_args) not loaded.")
        raise HTTPException(status_code=500, detail="Server configuration not loaded.")

    traces = []
    trace_count = 0  # Initialize count
    db_path = parsed_args.db
    logger.info(f"Attempting to fetch traces from DB: {db_path}")
    conn = None
    try:
        logger.info("Attempting to connect to DB...")
        conn = get_db_connection(db_path=db_path)
        logger.info("DB connection successful.")
        cursor = conn.cursor()
        logger.info("Executing SQL query for trace list...")
        sql = """
            SELECT trace_id, MIN(start_time) as trace_start_time, COUNT(span_id) as span_count
            FROM spans
            GROUP BY trace_id
            ORDER BY trace_start_time DESC
            LIMIT 50
        """
        cursor.execute(sql)
        logger.info("SQL query executed.")
        traces = cursor.fetchall()  # Fetch directly into traces variable
        trace_count = len(traces)  # Get count from fetched data
        logger.info(f"Fetched {trace_count} trace groups.")

    except sqlite3.Error as e:
        logger.error(
            f"Database error fetching trace list from {db_path}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Database query error fetching trace list."
        ) from e
    except Exception as e:
        logger.error(
            f"Unexpected error fetching trace list from {db_path}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=500, detail="Unexpected error fetching trace list."
        ) from e
    finally:
        if conn:
            logger.info("Closing DB connection.")
            conn.close()

    logger.info("Rendering index.html template.")
    return templates.TemplateResponse(
        "index.html", {"request": request, "traces": traces}
    )


@app.get("/trace/{trace_id}", response_class=HTMLResponse)
async def read_trace(request: Request, trace_id: str):
    """Display the details of a specific trace, showing all its spans."""
    if not parsed_args:
        raise HTTPException(status_code=500, detail="Server configuration not loaded.")

    spans = []
    db_path = parsed_args.db
    try:
        conn = get_db_connection(db_path=db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time ASC",
            (trace_id,),
        )
        raw_spans = cursor.fetchall()
        conn.close()

        # Basic processing: Parse JSON fields
        for raw_span in raw_spans:
            span_dict = dict(raw_span)
            for key in ["attributes", "events", "links", "resource"]:
                if span_dict.get(key):
                    try:
                        span_dict[key] = json.loads(span_dict[key])
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Could not parse JSON for {key} in span {span_dict.get('span_id')}"
                        )
                        # Keep the raw string if parsing fails
            spans.append(span_dict)

    except sqlite3.Error as e:
        logger.error(f"Database error fetching trace {trace_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Database error") from e
    except Exception as e:
        logger.error(f"Unexpected error fetching trace {trace_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e

    if not spans:
        raise HTTPException(status_code=404, detail="Trace not found")

    return templates.TemplateResponse(
        "trace_detail.html", {"request": request, "trace_id": trace_id, "spans": spans}
    )


# --- Main execution (for running directly) --- #

if __name__ == "__main__":
    import uvicorn

    # Argument parsing now happens in startup event
    # We still need host/port for uvicorn.run itself
    parser = argparse.ArgumentParser(description="Run the TinyAgent Traceboard server.")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host to bind the server to."
    )
    parser.add_argument(
        "--port", type=int, default=8008, help="Port to bind the server to."
    )
    # Add --db here just so uvicorn doesn't complain about unknown arg,
    # but it's primarily used by the startup event.
    parser.add_argument("--db", type=str, default="traces.db")
    args = parser.parse_args()

    print(f"Starting Traceboard server. Access at http://{args.host}:{args.port}")
    print(f"Template directory: {TEMPLATE_DIR}")
    # Note: DB path confirmation print is now in startup_event

    # Check if template dir exists
    if not TEMPLATE_DIR.exists() or not (TEMPLATE_DIR / "index.html").exists():
        print(
            f"\nWARNING: Template directory or index.html not found at {TEMPLATE_DIR}"
        )
        print(
            "Please create the templates/ directory with index.html and trace_detail.html"
        )
        print("Dashboard may not function correctly.")

    # Uvicorn will run the app, which triggers the startup event for arg parsing
    uvicorn.run(
        "traceboard:app", host=args.host, port=args.port, log_level="debug", reload=True
    )
