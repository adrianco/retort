# Summary: effort=high_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 3

- **Shape:** Go `net/http` (1.22+ method-pattern routing) CRUD API backed by SQLite via the pure-Go `modernc.org/sqlite` driver.
- **Structure:** 3 source modules + 1 test file (`main.go`, `store.go`, `handlers.go`, `handlers_test.go`); 335 non-test LOC.
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), one `books` SQLite table, `Store`/`Handler` library API.
- **Notable:** clean separation of store vs. handlers; defensive extras beyond spec (1 MiB body cap, `DisallowUnknownFields`, `Location` header, single-conn SQLite for write serialisation, persistence-across-reopen test). Validation uses 422 rather than the 400 hinted in the requirements.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
