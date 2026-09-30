# Summary: effort=high · model=claude-sonnet-5-5 · prompt=neutral · rep 1

- **Shape:** Zero-dependency Python REST API — stdlib `wsgiref` WSGI app over `sqlite3`, threaded server.
- **Structure:** 1 source module (`app.py`, 250 LOC), 1 test file (`test_app.py`, 8 functions), README + requirements.
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 SQLite table, `create_app()`/`validate_book()` exported.
- **Notable:** Uses only the standard library (no Flask/FastAPI) — the leanest approach for this task. Thorough error taxonomy (400/404/405/413/422/500), per-request connections, case-insensitive author filter, 1 MB body cap.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
