# Summary: effort=medium_language=python_model=claude-opus-5-5_prompt=neutral · rep 3

- **Shape:** Dependency-free Python WSGI REST API (`wsgiref` + stdlib `sqlite3`), no web framework.
- **Structure:** 2 source modules (`app.py`, `test_app.py`), 1 test file, README.
- **Interfaces:** 6 HTTP routes (`/health`, `/books` GET/POST, `/books/{id}` GET/PUT/DELETE), 1 `books` table.
- **Notable:** Zero third-party runtime deps; thread-safe SQLite store behind a lock; strict input validation; 49 tests including a real-socket end-to-end run and SQL-injection/`?author=` edge cases.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
