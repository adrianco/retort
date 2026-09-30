# Summary: effort=low_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 1

- **Shape:** Go `net/http` (stdlib, 1.22+ routing) CRUD API backed by pure-Go SQLite (`modernc.org/sqlite`, no cgo).
- **Structure:** 2 source modules (main.go, store.go) + 1 test file.
- **Interfaces:** 6 HTTP routes, 6 exported `Store` methods, 1 `books` table.
- **Notable:** Compact and idiomatic — clean handler/store split, shared `decode`/`pathID`/`fail` helpers, 1 MiB body cap, `sql.ErrNoRows`→404 mapping. No external web framework.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
