# Summary: agent=codex model=gpt-6-astra language=python prompt=neutral · rep 2

- **Shape:** Stdlib-only Python MCP stdio server (JSON-RPC 2.0) over an in-memory soccer knowledge graph built from 6 Kaggle CSVs.
- **Structure:** 2 source modules (`soccer.py`, `server.py`) + 1 test module (20 tests), zero third-party dependencies.
- **Interfaces:** 5 MCP methods, 10 reflected tools, 2 entity types (match, player); CLI entrypoint `python server.py`.
- **Notable:** Tool schemas auto-generated from method signatures via `inspect`; cross-source fixture deduplication with ±1-day tolerance; dense, comment-light one-liner style in the query layer; no `pandas`/`fastmcp` — everything on `csv`/`unicodedata`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
