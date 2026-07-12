# Summary: agent=hermes-local language=go prompt=neutral · rep 2

- **Shape:** Go `net/http` CRUD REST API backed by SQLite (`mattn/go-sqlite3`), single-file (`main.go`).
- **Structure:** 1 source module + 1 test file (15 tests), testify assertions.
- **Interfaces:** 6 HTTP routes (health + 5 book CRUD, with `?author=` filter and id-by-path).
- **Notable:** Clean idiomatic stdlib routing (no web framework despite README claiming gorilla/mux); presence-only validation; `updateBook` echoes the request body instead of the persisted row.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
