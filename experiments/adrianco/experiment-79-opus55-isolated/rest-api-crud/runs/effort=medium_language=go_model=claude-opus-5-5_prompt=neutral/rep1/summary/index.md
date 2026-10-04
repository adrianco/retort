# Summary: effort=medium language=go model=claude-opus-5-5 prompt=neutral · rep 1

- **Shape:** Go `net/http` (1.22+ method+pattern routing) CRUD API backed by pure-Go SQLite (`modernc.org/sqlite`).
- **Structure:** 3 source modules + 1 test file (456 source LOC, 353 test LOC).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), one `books` table.
- **Notable:** No third-party web/router framework — stdlib only. Graceful shutdown, 1 MiB body cap, JSON-ified 404/405, parameterized queries with an SQL-injection test, and a persistence-across-reopen test. Clean layered separation (main/handlers/store).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
