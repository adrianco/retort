# Summary: effort=default_language=go_model=claude-opus-5-5_prompt=neutral · rep 3

- **Shape:** Go `net/http` CRUD REST API over SQLite (pure-Go `modernc.org/sqlite`, no cgo)
- **Structure:** 3 source modules + 1 test file (718 LOC total, 301 in tests)
- **Interfaces:** 6 HTTP routes, 1 `books` table, 2 env-var config knobs
- **Notable:** Idiomatic stdlib-only routing (Go 1.22 method patterns); graceful shutdown; parameterized queries with an explicit SQL-injection regression test; strict JSON decoding rejecting trailing data; validation returns per-field error details.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
