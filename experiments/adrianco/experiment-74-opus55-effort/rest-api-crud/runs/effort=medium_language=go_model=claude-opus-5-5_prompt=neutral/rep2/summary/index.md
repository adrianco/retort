# Summary: effort=medium language=go model=claude-opus-5-5 prompt=neutral · rep 2

- **Shape:** Go `net/http` (1.22 method+path patterns) CRUD REST API backed by SQLite via the pure-Go `modernc.org/sqlite` driver (no CGO).
- **Structure:** 3 source modules (main/handlers/store) + 1 test file (7 tests, 8 subtests); 395 source LOC, 230 test LOC.
- **Interfaces:** 6 HTTP routes (health + full CRUD), 1 `books` table, `Store` CRUD API.
- **Notable:** graceful shutdown with signal context, request-body size cap + `DisallowUnknownFields`, ISBN-10/13 validation, 422 for validation vs 400 for malformed input, case-insensitive author filter. Clean idiomatic separation of concerns.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
