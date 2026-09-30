# Summary: effort=high language=python model=claude-sonnet-5-5 prompt=neutral · rep 2

- **Shape:** Pure-stdlib Python WSGI REST API (`wsgiref` + `sqlite3`), zero third-party runtime deps.
- **Structure:** 1 source module (`app.py`), 1 test file (`tests/test_api.py`, 11 tests).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 SQLite table, `create_app()` factory.
- **Notable:** Hand-rolled router with regex path matching and a per-request SQLite connection; no framework, yet full validation, status-code discipline, and cross-instance persistence tests.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
