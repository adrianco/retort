# Summary: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 2

- **Shape:** Go `net/http` CRUD REST API backed by SQLite (`mattn/go-sqlite3`), single-file implementation.
- **Structure:** 1 source module (`main.go`), 1 test file (`main_test.go`, 4 tests).
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 SQLite table, `NewAPI` constructor implementing `http.Handler`.
- **Notable:** Tight, idiomatic stdlib-only routing (no framework); parameterized SQL throughout; strict JSON decoding (`DisallowUnknownFields`, `MaxBytesReader`); `405` with `Allow` header for wrong methods.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
