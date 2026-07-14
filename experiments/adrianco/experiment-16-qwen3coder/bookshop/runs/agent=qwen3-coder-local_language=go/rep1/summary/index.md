# Summary: agent=qwen3-coder-local language=go · rep 1

- **Shape:** Go `net/http` CRUD REST API with SQLite (`mattn/go-sqlite3`) persistence, single-file.
- **Structure:** 1 source module (`main.go`), 1 test file (`main_test.go`, 8 subtests).
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); `BookStore` exposes 8 methods over a `books` SQLite table.
- **Notable:** Two parallel `/books/{id}` handler implementations — `main()` wires the `handle*WithID` variants, but the tests call the standalone `handleGetBook`/`handleUpdateBook`/`handleDeleteBook`, so the production path is untested (matches the 45.2% coverage). `UpdateBook`/`DeleteBook` have dead `sql.ErrNoRows` branches, so missing-ID updates/deletes return 200 not 404.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
