# Summary: effort=default·language=go·model=claude-sonnet-5-5·prompt=neutral · rep 1

- **Shape:** Go `net/http` (Go 1.22 method-pattern mux) CRUD REST API over SQLite via pure-Go `modernc.org/sqlite` (no CGO).
- **Structure:** 2 source modules (`main.go`, `store.go`) + 1 test file (`main_test.go`).
- **Interfaces:** 6 HTTP routes (health + 5 book CRUD), 1 `books` table.
- **Notable:** Clean separation of HTTP layer (`main.go`) from persistence (`store.go`); dependency injection via `NewServer(*Store)` makes it trivially testable with `:memory:`; validation trims whitespace and rejects negative years beyond the spec's minimum.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
