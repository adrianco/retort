# Summary: agent=hermes-local language=go prompt=none stack=s4 · rep 1

- **Shape:** Go + Gin REST API with SQLite (`mattn/go-sqlite3`), single-file `app.go` using `database/sql` directly.
- **Structure:** 1 source module (`app.go`) + 1 test file (`app_test.go`, 13 tests); flat package `main`.
- **Interfaces:** 6 HTTP routes (health + 5 book CRUD), 1 `books` SQLite table, no CLI or exported library API.
- **Notable:** Global `*sql.DB` swapped out in tests rather than injected; double validation (Gin `binding:"required"` + manual checks); PUT is a read-modify-write partial update where empty/zero values fall back to existing data.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
