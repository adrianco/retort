# Summary: agent=hermes-local language=go prompt=none stack=s3 · rep 1

- **Shape:** Go + Gin REST API with SQLite (go-sqlite3) persistence — CRUD over a `books` collection.
- **Structure:** 1 source module (app.go) + 1 test module (app_test.go), 6 test functions (13 subtests).
- **Interfaces:** 6 HTTP routes (5 CRUD + health), 0 CLI commands, 0 exported library functions.
- **Notable:** Idiomatic Gin structure with parameterized SQL (no injection), `binding:"required"` validation, in-memory SQLite for tests. Partial-update semantics use empty-string/zero as "unchanged" sentinels, so a field cannot be explicitly cleared or set to year 0.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
