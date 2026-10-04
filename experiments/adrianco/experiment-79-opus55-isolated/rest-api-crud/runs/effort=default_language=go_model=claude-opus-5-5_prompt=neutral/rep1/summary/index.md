# Summary: rest-api-crud · effort=default language=go model=claude-opus-5-5 prompt=neutral · rep 1

- **Shape:** Go `net/http` (1.22 routing) CRUD API over a pure-Go SQLite store (`modernc.org/sqlite`, no cgo).
- **Structure:** 3 source modules + 1 test file (12 test functions, many table-driven subtests).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`); `?author=` exact filter; per-field 400 validation.
- **Notable:** Standard-library-only routing (no framework), graceful shutdown, 1 MiB body cap, single-object body enforcement, parameterised queries with a SQL-injection regression test. Clean, idiomatic, no skipped tests.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
