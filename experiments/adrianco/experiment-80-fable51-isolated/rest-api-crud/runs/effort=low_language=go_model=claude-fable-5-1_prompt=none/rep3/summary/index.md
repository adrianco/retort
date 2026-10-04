# Summary: effort=low language=go model=claude-fable-5-1 prompt=none · rep 3

- **Shape:** Go `net/http` (Go 1.22 method-pattern router) CRUD service backed by SQLite via the pure-Go `modernc.org/sqlite` driver.
- **Structure:** 1 source module (`main.go`) + 1 test file (`main_test.go`), plus `README.md`, `go.mod`, `go.sum`.
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 `books` table.
- **Notable:** Idiomatic single-file design; uses stdlib method-pattern routing (`GET /books/{id}`) with no third-party web framework. Pins `SetMaxOpenConns(1)` for `:memory:`/SQLite consistency and adds a `MaxBytesReader` body cap and `Location` header on create — small touches beyond the spec.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
