# Summary: agent=hermes-local language=go prompt=none stack=s8 · rep3

- **Shape:** Go / Gin REST API backed by SQLite (`mattn/go-sqlite3`), single-package binary.
- **Structure:** 1 source module (`app.go`), 1 test file (`app_test.go`) with 23 test functions plus `TestMain`.
- **Interfaces:** 6 HTTP routes (health + full book CRUD with `?author=` filter); one `books` table; no CLI or exported library API.
- **Notable:** Uses raw `database/sql` with parameterized queries (no ORM); `validateBook` only enforces non-empty title/author and returns its message via a string rather than an `error`; ISBN uniqueness enforced only by the DB constraint, surfaced as a generic 500; DB file is hardcoded to `./books.db`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
