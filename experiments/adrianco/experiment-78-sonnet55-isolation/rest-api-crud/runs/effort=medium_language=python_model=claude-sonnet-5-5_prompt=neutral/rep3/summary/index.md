# Summary: effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 3

- **Shape:** Zero-dependency Python REST API — stdlib `wsgiref` WSGI app over SQLite.
- **Structure:** 1 source module (`app.py`, 143 LOC), 1 test file (`tests/test_api.py`, 5 test functions), README.
- **Interfaces:** 6 HTTP routes (5 CRUD + health), 1 SQLite table, `create_app()` factory.
- **Notable:** Uses only the standard library (no Flask/FastAPI) — a compact, idiomatic-stdlib approach. Per-request SQLite connection with `:memory:` special-casing; central `HTTPError`→JSON error handling.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
