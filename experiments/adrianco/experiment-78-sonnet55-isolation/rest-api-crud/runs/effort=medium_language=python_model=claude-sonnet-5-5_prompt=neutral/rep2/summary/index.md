# Summary: effort=medium language=python model=claude-sonnet-5-5 prompt=neutral · rep 2

- **Shape:** Python stdlib WSGI REST API (`wsgiref` + `sqlite3`), zero third-party runtime deps
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 6 tests)
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`), 1 SQLite table
- **Notable:** Unusually compact — the whole service is ~142 lines with a hand-rolled router and a thread-locked shared connection, avoiding Flask/FastAPI entirely.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
