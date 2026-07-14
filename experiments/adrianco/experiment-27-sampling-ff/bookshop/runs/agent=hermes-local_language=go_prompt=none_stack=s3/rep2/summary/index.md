# Summary: agent=hermes-local language=go prompt=none stack=s3 · rep 2

- **Shape:** Go + Gin REST API with SQLite (go-sqlite3) persistence.
- **Structure:** 1 source module (`app.go`), 1 test file (`app_test.go`, 12 tests), README.
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`); 1 `books` table.
- **Notable:** Clean, idiomatic CRUD; parameterized SQL throughout; partial-update via zero-value substitution; tests run against `:memory:` SQLite so they exercise real handler + DB code.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
