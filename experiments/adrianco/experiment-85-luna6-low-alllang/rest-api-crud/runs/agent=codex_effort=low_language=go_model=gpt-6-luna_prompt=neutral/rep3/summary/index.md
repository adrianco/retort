# Summary: agent=codex effort=low language=go model=gpt-6-luna prompt=neutral · rep 3

- **Shape:** Go `net/http` CRUD service backed by embedded SQLite (`modernc.org/sqlite`, pure Go — no cgo).
- **Structure:** 1 source module (`main.go`), 1 test file (`main_test.go`, 3 tests); ~375 LOC total.
- **Interfaces:** 6 HTTP routes (health + full books CRUD with `?author=` filter); exported `API`, `Book`, `NewAPI`, `OpenDB`.
- **Notable:** Hand-rolled router (no web framework); strict JSON decoding (`DisallowUnknownFields`, trailing-data rejection, 1 MiB cap); parameterized SQL; configurable via `ADDR`/`BOOKS_DB` env vars.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
