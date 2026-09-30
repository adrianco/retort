# Summary: effort=default·language=python·model=claude-sonnet-5-5·prompt=neutral · rep 1

- **Shape:** Pure-stdlib Python REST API (`http.server` + `sqlite3`) — zero third-party runtime dependencies.
- **Structure:** 1 source module (`app.py`), 1 test file (6 tests), README.
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), backed by a single `books` SQLite table.
- **Notable:** Chose the standard library over a framework (Flask/FastAPI) — compact (171 LOC) and dependency-free, with thread-safe access via one lock and a shared connection.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
