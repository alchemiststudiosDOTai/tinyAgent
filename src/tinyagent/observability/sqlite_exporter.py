import logging
import sqlite3
import json
from typing import Sequence, Optional, Tuple, Any

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import Span

logger = logging.getLogger(__name__)

# Define database schema and initialization logic
DB_SCHEMA = '''
CREATE TABLE IF NOT EXISTS spans (
    trace_id TEXT,
    span_id TEXT,
    parent_span_id TEXT NULL,
    name TEXT,
    start_time INTEGER,
    end_time INTEGER,
    duration INTEGER,
    status_code TEXT,
    status_message TEXT NULL,
    attributes TEXT, -- Store as JSON string
    events TEXT, -- Store as JSON string
    links TEXT, -- Store as JSON string
    kind INTEGER,
    resource TEXT, -- Store as JSON string
    library_name TEXT,
    library_version TEXT
);
'''

class SQLiteSpanExporter(SpanExporter):
    """
    An OpenTelemetry SpanExporter that writes spans to a SQLite database.

    This exporter is intended for simple local observability scenarios
    without requiring external services or Docker.
    """

    def __init__(self, db_path: str = "traces.db"):
        print(f"--- [SQLiteSpanExporter] Initializing with db_path: {db_path} ---") # DEBUG
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._cursor: Optional[sqlite3.Cursor] = None
        self._connect()
        self._initialize_db()
        print(f"--- [SQLiteSpanExporter] Initialization complete. Connection: {self._conn is not None} ---") # DEBUG

    def _connect(self):
        print(f"--- [SQLiteSpanExporter] Attempting to connect to DB: {self.db_path} ---") # DEBUG
        try:
            # isolation_level=None enables autocommit mode for simplicity here
            # check_same_thread=False might be needed if accessed from multiple threads,
            # but OTel SDK usually handles export in a dedicated thread.
            self._conn = sqlite3.connect(self.db_path, isolation_level=None, check_same_thread=False)
            self._cursor = self._conn.cursor()
            print(f"--- [SQLiteSpanExporter] Successfully connected to DB: {self.db_path} ---") # DEBUG
            logger.info(f"Connected to SQLite trace database: {self.db_path}")
        except sqlite3.Error as e:
            print(f"--- [SQLiteSpanExporter] FAILED to connect to DB: {e} ---") # DEBUG
            logger.error(f"Failed to connect to SQLite DB at {self.db_path}: {e}", exc_info=True)
            self._conn = None
            self._cursor = None
        except Exception as e:
             print(f"--- [SQLiteSpanExporter] UNEXPECTED error connecting to DB: {e} ---") # DEBUG
             logger.error(f"Unexpected error connecting to SQLite DB: {e}", exc_info=True)
             self._conn = None
             self._cursor = None

    def _initialize_db(self):
        print(f"--- [SQLiteSpanExporter] Initializing DB schema (Cursor exists: {self._cursor is not None}) ---") # DEBUG
        if not self._cursor:
            print("--- [SQLiteSpanExporter] Cannot initialize DB: No cursor. ---") # DEBUG
            logger.warning("Cannot initialize DB: No cursor.")
            return
        try:
            self._cursor.execute(DB_SCHEMA)
            print("--- [SQLiteSpanExporter] DB schema check/creation executed successfully. ---") # DEBUG
            logger.debug("Executed DB schema check/creation.")
        except sqlite3.Error as e:
            print(f"--- [SQLiteSpanExporter] FAILED to initialize DB schema: {e} ---") # DEBUG
            logger.error(f"Failed to initialize SQLite DB schema: {e}", exc_info=True)
        except Exception as e:
            print(f"--- [SQLiteSpanExporter] UNEXPECTED error initializing DB schema: {e} ---") # DEBUG
            logger.error(f"Unexpected error initializing DB schema: {e}", exc_info=True)

    def export(self, spans: Sequence[Span]) -> SpanExportResult:
        """Exports a batch of spans to the SQLite database."""
        if not self._conn or not self._cursor:
            logger.error("Cannot export spans: No database connection.")
            return SpanExportResult.FAILURE

        insert_sql = '''
            INSERT INTO spans (
                trace_id, span_id, parent_span_id, name, start_time, end_time, duration,
                status_code, status_message, attributes, events, links, kind,
                resource, library_name, library_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''

        rows_to_insert: list[Tuple] = []
        for span in spans:
            # Serialize complex types to JSON strings
            attributes_str = json.dumps(dict(span.attributes)) if span.attributes else None
            events_str = json.dumps([event.__dict__ for event in span.events]) if span.events else None # Basic event serialization
            links_str = json.dumps([link.__dict__ for link in span.links]) if span.links else None # Basic link serialization
            resource_str = json.dumps(dict(span.resource.attributes)) if span.resource else None
            parent_span_id = format(span.parent.span_id, '016x') if span.parent else None

            # Convert nanoseconds to milliseconds for storage (or keep as ns if preferred)
            start_ms = span.start_time // 1000000 if span.start_time else None
            end_ms = span.end_time // 1000000 if span.end_time else None
            duration_ms = (span.end_time - span.start_time) // 1000000 if span.end_time and span.start_time else 0

            row_data: Tuple[Any, ...] = (
                format(span.context.trace_id, '032x'),
                format(span.context.span_id, '016x'),
                parent_span_id,
                span.name,
                start_ms, # Storing as ms
                end_ms, # Storing as ms
                duration_ms, # Storing as ms
                span.status.status_code.name,
                span.status.description,
                attributes_str,
                events_str,
                links_str,
                span.kind.value,
                resource_str,
                span.instrumentation_scope.name if span.instrumentation_scope else None,
                span.instrumentation_scope.version if span.instrumentation_scope else None,
            )
            rows_to_insert.append(row_data)

        try:
            self._cursor.executemany(insert_sql, rows_to_insert)
            logger.debug(f"Exported {len(spans)} spans to SQLite.")
            return SpanExportResult.SUCCESS
        except sqlite3.Error as e:
            logger.error(f"Failed to insert spans into SQLite: {e}", exc_info=True)
            return SpanExportResult.FAILURE
        except Exception as e:
            logger.error(f"Unexpected error during SQLite export: {e}", exc_info=True)
            return SpanExportResult.FAILURE

    def shutdown(self):
        """Closes the database connection."""
        if self._conn:
            try:
                self._conn.close()
                logger.info("SQLite trace exporter connection closed.")
            except sqlite3.Error as e:
                logger.error(f"Error closing SQLite connection: {e}", exc_info=True)
        self._conn = None
        self._cursor = None

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Force flush spans. SQLite operates in autocommit mode here,
        so this is effectively a no-op.
        """
        # In autocommit mode, writes happen immediately.
        # If we used transactions, we'd commit here.
        logger.debug("force_flush called on SQLite exporter (autocommit mode). No action needed.")
        return True

# Example Usage (for testing purposes)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    exporter = SQLiteSpanExporter(db_path="./test_traces.db")
    # Simulate some spans (replace with actual OTel span creation if needed)
    # This part requires opentelemetry-sdk to create actual Span objects
    # For now, just ensuring the class structure is sound.
    print("SQLiteSpanExporter initialized. Run with OpenTelemetry SDK to test export.")
    exporter.shutdown()
    print("SQLiteSpanExporter shut down.") 