# Summary: effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 1

- **Shape:** Zero-dependency Python REST API on the stdlib `http.server` + `sqlite3`.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 8 tests), README.
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`), 1 SQLite table.
- **Notable:** No framework and no dependencies — routing is a hand-written regex/path dispatcher; a `threading.Lock` guards the shared connection under `ThreadingHTTPServer`. Compact and idiomatic for a stdlib-only solution.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
