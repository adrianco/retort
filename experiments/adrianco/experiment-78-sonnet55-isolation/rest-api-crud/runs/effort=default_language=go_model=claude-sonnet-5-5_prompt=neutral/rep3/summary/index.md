# Summary: effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 3

- **Shape:** Go stdlib `net/http` CRUD API backed by SQLite via pure-Go `modernc.org/sqlite` (no CGO).
- **Structure:** 1 source module (`main.go`), 1 test file (`main_test.go`, 4 tests).
- **Interfaces:** 6 HTTP routes (5 `/books` CRUD + `/health`); one `books` table.
- **Notable:** Compact, idiomatic single-file design using Go 1.22 method+path routing (`GET /books/{id}`). Parameterized SQL throughout; `MaxBytesReader` body cap; validation includes a non-obvious negative-year check.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
