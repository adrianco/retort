# Summary: effort=high language=go model=claude-opus-5-5 prompt=neutral · rep 3

- **Shape:** Go `net/http` (1.22+ method-based routing) REST CRUD API backed by SQLite via the pure-Go `modernc.org/sqlite` driver.
- **Structure:** 3 source modules (main, store, handlers) + 2 test files (12 test functions total).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 `books` table, ~7 exported store/server functions.
- **Notable:** production-grade extras beyond spec — graceful shutdown, request-size cap, structured slog logging, `Allow`-header 405s, WAL pragmas, and URI-metacharacter-safe DSN escaping. No third-party web framework.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
