# Summary: effort=high_language=go_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** Go `net/http` (1.22+ routing) CRUD API over SQLite via pure-Go `modernc.org/sqlite`.
- **Structure:** 3 source modules + 1 test file (15 test functions).
- **Interfaces:** 6 HTTP routes; `Store` interface (7 methods) with one SQLite impl.
- **Notable:** No third-party web/ORM framework — stdlib router only; clean store/handler
  separation, graceful shutdown, 1 MiB body cap, LIKE-wildcard escaping, single-writer
  connection, and a `now` injection point that makes year-validation deterministic in tests.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
