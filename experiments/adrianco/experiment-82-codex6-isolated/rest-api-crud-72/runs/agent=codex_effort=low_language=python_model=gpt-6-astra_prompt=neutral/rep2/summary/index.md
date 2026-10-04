# Summary: agent=codex_effort=low_language=python_model=gpt-6-astra_prompt=neutral · rep 2

- **Shape:** Flask REST API (application factory) over the stdlib `sqlite3` driver, no ORM.
- **Structure:** 1 source module (`app.py`), 1 test file (`test_app.py`, 8 unittest methods).
- **Interfaces:** 6 HTTP routes, 1 exported function (`create_app`), 1 SQLite table.
- **Notable:** all routes are closures inside `create_app()`; a single `HTTPException` handler converts every error to `{"error": ...}` JSON; unknown request fields are rejected; POST returns a `Location` header.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
