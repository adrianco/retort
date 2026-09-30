# Summary: effort=high language=go model=claude-sonnet-5-5 prompt=neutral · rep 1

- **Shape:** Go `net/http` (1.22 ServeMux) CRUD API over SQLite (`modernc.org/sqlite`, pure Go, no CGO).
- **Structure:** 3 source modules (main/handlers/store) + 1 test file (6 test functions), ~562 LOC.
- **Interfaces:** 6 HTTP routes (5 `/books` + `/health`); `Store` with 7 exported methods; one `books` table.
- **Notable:** strict JSON decoding (unknown-field/trailing-data/body-size guards), 201+`Location`, 204 on delete, health check pings the DB, persistence verified across DB reopen. Clean, idiomatic stdlib-only approach.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
