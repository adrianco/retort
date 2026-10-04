# Summary: effort=default language=go model=claude-fable-5-1 prompt=neutral · rep 1

- **Shape:** Go `net/http` CRUD REST API backed by SQLite (pure-Go `modernc.org/sqlite` driver).
- **Structure:** 4 source modules (main, handlers, store, tests), 1 test file.
- **Interfaces:** 6 HTTP routes (+ JSON 404/405 fallthrough), 1 `books` table.
- **Notable:** Uses Go 1.22+ method-aware `ServeMux` patterns (`"POST /books"`, `{id}`), wraps the mux to convert plain-text 404/405 into JSON, single-connection SQLite for `:memory:` consistency, and validation that reports all problems at once.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
