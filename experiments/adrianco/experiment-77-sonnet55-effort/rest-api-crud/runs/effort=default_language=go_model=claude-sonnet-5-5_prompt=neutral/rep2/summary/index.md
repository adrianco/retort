# Summary: effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 2

- **Shape:** Go `net/http` CRUD REST API backed by SQLite (pure-Go `modernc.org/sqlite`, no cgo).
- **Structure:** 2 source modules (main.go, store.go) + 1 test file (main_test.go).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 8 exported `Store` methods, one `books` table.
- **Notable:** Uses Go 1.22+ method-and-path routing (`GET /books/{id}`) with no third-party web framework; a clean handler/store split; validation trims whitespace and rejects negative years; single-connection pool for `:memory:` consistency.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
