# Summary: effort=low_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 2

- **Shape:** Python stdlib REST API (`http.server` + `sqlite3`), no third-party runtime deps.
- **Structure:** 1 source module (app.py), 1 test file (5 tests).
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter); 1 SQLite table.
- **Notable:** Zero-dependency approach — hand-rolled router with a regex on `/books/{id}`, thread-safe store via a single lock. Compact (170 LOC).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
