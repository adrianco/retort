# Summary: effort=xhigh_language=go_model=claude-haiku-5-5_prompt=neutral · rep 2

- **Shape:** Go `net/http` REST API (Go 1.22 method-pattern routing) over a pure-Go embedded SQLite store (`modernc.org/sqlite`), with a clean domain/store/server layering.
- **Structure:** 5 source modules across 3 internal packages (`book`, `store`, `server`) plus `main.go`; 3 test files (24 test functions).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD) plus method-not-allowed and 404 catch-alls; one `books` SQLite table.
- **Notable:** No third-party web framework — stdlib router only. Goes well beyond the spec: graceful shutdown, request logging middleware, ISBN-10/13 check-digit validation, body-size limits, `DisallowUnknownFields`, 405 with `Allow` header, and WAL + busy_timeout pragmas.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
