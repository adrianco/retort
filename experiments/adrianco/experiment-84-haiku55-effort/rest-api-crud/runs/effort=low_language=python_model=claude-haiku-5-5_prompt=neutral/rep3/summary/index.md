# Summary: effort=low_language=python_model=claude-haiku-5-5_prompt=neutral · rep 3

- **Shape:** Python stdlib REST API (`http.server` + `sqlite3`), zero third-party runtime deps
- **Structure:** 1 source module, 1 test file (12 tests), 1 README
- **Interfaces:** 6 HTTP routes (full CRUD + author filter + health), 1 SQLite table
- **Notable:** No framework or ORM — hand-rolled routing with regex path matching and a
  lock-guarded shared connection; validation, 409-on-duplicate-ISBN, and a `Location`
  header go beyond the minimum spec.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
