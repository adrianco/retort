# Summary: agent=codex effort=low language=go model=gpt-6.2-astra prompt=neutral · rep 1

- **Shape:** Go `net/http` CRUD API backed by SQLite (`mattn/go-sqlite3`), no web framework.
- **Structure:** 1 source module (`main.go`, 192 LoC) + 1 test file (3 test functions), 270 LoC total.
- **Interfaces:** 6 HTTP routes (full CRUD + `/health`), single `api.ServeHTTP` path-switch dispatcher.
- **Notable:** Very compact and idiomatic — centralized error-to-status mapping, `RETURNING id` for both insert and update, `DisallowUnknownFields` + trailing-data rejection for strict request bodies, `SetMaxOpenConns(1)` to avoid SQLite write contention. No external router dependency.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
