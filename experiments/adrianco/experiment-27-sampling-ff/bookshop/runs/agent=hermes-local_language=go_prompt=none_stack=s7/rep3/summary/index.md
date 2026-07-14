# Summary: agent=hermes-local language=go prompt=none stack=s7 · rep 3

- **Shape:** Go Gin REST API for a book collection, backed by SQLite (mattn/go-sqlite3) with a raw `database/sql` layer.
- **Structure:** 1 source module (`app.go`), 1 test file (`app_test.go`) with 16 `Test*` functions + `TestMain`.
- **Interfaces:** 6 HTTP routes (health + full CRUD with `?author=` filter); no CLI; ~11 exported Go symbols.
- **Notable:** All logic lives in a single flat `app.go` (no packages/layers); manual field validation rather than gin `binding` tags; `books` table auto-created on startup; server hardcoded to `:8080` and DB to `books.db`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
