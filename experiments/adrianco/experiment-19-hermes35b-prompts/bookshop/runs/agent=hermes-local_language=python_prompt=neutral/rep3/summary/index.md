# Summary: agent=hermes-local language=python prompt=neutral · rep 3

- **Shape:** Flask REST API with raw `sqlite3` (no ORM), single-module app.
- **Structure:** 1 source module + 1 test module (18 tests), README + requirements.
- **Interfaces:** 7 HTTP routes (full CRUD + `?author=` filter + `/health`), 1 SQLite table.
- **Notable:** Clean idiomatic Flask — per-request connection on `flask.g` with `teardown_appcontext`, WAL mode, parameterized queries, whitespace-stripping validation on both create and update. Author filter uses `LIKE` substring match.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
