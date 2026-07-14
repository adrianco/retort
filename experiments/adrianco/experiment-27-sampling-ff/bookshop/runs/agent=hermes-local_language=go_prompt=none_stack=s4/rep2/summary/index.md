# Summary: agent=hermes-local language=go prompt=none stack=s4 · rep 2

- **Shape:** Go + Gin REST API with SQLite (go-sqlite3) persistence.
- **Structure:** 1 source module (`app.go`), 1 test file (`app_test.go`, 13 tests).
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`), 1 `books` table.
- **Notable:** Clean, complete CRUD with existence checks and a defensive whitespace re-validation on top of Gin's `binding:"required"`; partial-update semantics use Go zero-values as "unset", so `year=0`/empty fields can't be set explicitly.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
