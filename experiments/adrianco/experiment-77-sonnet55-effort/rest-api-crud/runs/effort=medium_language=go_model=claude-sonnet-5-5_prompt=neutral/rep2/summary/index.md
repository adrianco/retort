# Summary: rest-api-crud · effort=medium language=go model=claude-sonnet-5-5 prompt=neutral · rep 2

- **Shape:** Go `net/http` CRUD REST API over SQLite (`modernc.org/sqlite`, pure-Go driver), using Go 1.22+ method-prefixed `ServeMux` routing.
- **Structure:** 3 source modules (`main.go`, `handlers.go`, `store.go`), 1 test file (4 test functions).
- **Interfaces:** 6 HTTP routes (health + full book CRUD with `?author=` filter); ~10 exported `Store`/handler functions; 1 `books` table.
- **Notable:** Clean handler/store separation; parameterized SQL, 1 MiB body cap, and negative-year validation beyond the required title/author checks; single-connection pool for `:memory:` consistency; tests exercise CRUD, validation edge cases, and the author filter against an in-memory DB.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
