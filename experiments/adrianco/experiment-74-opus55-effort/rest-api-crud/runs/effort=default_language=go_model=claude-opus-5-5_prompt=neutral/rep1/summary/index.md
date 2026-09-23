# Summary: effort=default·language=go·model=claude-opus-5-5·prompt=neutral · rep 1

- **Shape:** Go `net/http` (1.22 mux) CRUD REST API backed by SQLite via pure-Go `modernc.org/sqlite`.
- **Structure:** 3 source modules (main/store/handlers) + 1 test file (7 tests).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 SQLite table.
- **Notable:** cgo-free SQLite driver, graceful shutdown, `DisallowUnknownFields` + body-size cap, ISBN validation, case-insensitive author filter, generics-based test helpers. Clean beyond-spec hardening.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
