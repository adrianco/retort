# Summary: agent=hermes-local · language=go · prompt=repair · rep 2

- **Shape:** Go `net/http` ServeMux CRUD REST API backed by SQLite via `modernc.org/sqlite` (pure-Go driver, no cgo).
- **Structure:** 4 source modules (main, models, database, handlers) + 1 test file with 16 test functions.
- **Interfaces:** 6 HTTP routes (health + 5 book CRUD, with `?author=` filter), 1 `books` SQLite table, `BookRepository` interface abstracting persistence.
- **Notable:** Clean repository-interface separation; partial updates via pointer-field request struct; validation limited to title/author; a repair-task variant (fixed a prior failing attempt), manual path-ID parsing instead of a routing library.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
