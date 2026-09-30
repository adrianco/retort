# Summary: effort=medium_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 1

- **Shape:** Go `net/http` (1.22+ pattern routing) REST CRUD backed by real SQLite (pure-Go `modernc.org/sqlite`).
- **Structure:** 2 source modules (`main.go`, `store.go`) + 1 test file (`main_test.go`), ~388 total lines.
- **Interfaces:** 6 HTTP routes (health + 5 book CRUD), 1 `books` table, `Store` library API.
- **Notable:** Clean separation of HTTP (main.go) from persistence (store.go); sentinel-error → HTTP-status mapping; body-size cap; `Location` header on create; tests use `httptest` against `:memory:` SQLite. No external web framework — stdlib only.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
