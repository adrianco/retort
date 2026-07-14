# Summary: agent=hermes-local language=python prompt=none stack=s6 · rep 1

- **Shape:** Flask REST API with raw-sqlite3 persistence (WAL), single-module app.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 17 tests / 6 classes).
- **Interfaces:** 6 HTTP routes (5 CRUD + /health), 0 CLI commands, 0 exported library functions.
- **Notable:** `init_db()` runs on every request via `before_request` (not once at startup); author filter is a substring `LIKE` match; validation includes an out-of-spec year range check (0–2100).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
