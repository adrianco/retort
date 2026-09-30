# Summary: effort=high language=go model=claude-sonnet-5-5 prompt=neutral · rep 2

- **Shape:** Go `net/http` (1.22+ pattern router) CRUD REST API over SQLite (pure-Go `modernc.org/sqlite`).
- **Structure:** 3 source modules + 1 test file (7 test functions).
- **Interfaces:** 6 HTTP routes, 1 `books` table, a `Store` persistence API with 7 methods.
- **Notable:** No third-party web framework; strict JSON decoding (rejects trailing data), 1 MiB body cap, health check pings the DB, and a persistence-across-reopen test. Clean idiomatic layering (main → API → Store).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
