Change: Added Jina Reader example and optional API key support

- New example: `examples/jina_reader_demo.py`
  - Provides `@tool` `jina_scrape(url: str) -> str` using `https://r.jina.ai/<url>`
  - Uses stdlib `urllib` (no new dependency)
  - Loads `.env` if `python-dotenv` present
  - Optionally includes `Authorization: Bearer <JINA_API_KEY>` when `JINA_API_KEY` is set
- Removed root `interactive_jina.py` to avoid duplication
- README references the new example and notes optional `JINA_API_KEY`

Rationale: Make the ad-hoc script a proper example, keep deps tiny, and allow users with keys to pass them via env.
