Change: Add minimal spinner to Jina example

- Updated `examples/jina_reader_demo.py` to include a tiny `spinner()` context manager.
- Displays "Searching..." with dots while `agent.run(...)` executes.
- No new dependencies; uses stdlib `threading` and `time`.
- Keeps code minimal and clean per request.
