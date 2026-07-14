# Summary: agent=hermes-local language=go prompt=neutral · rep 3

- **Shape:** Go + Gin REST CRUD API backed by SQLite (go-sqlite3), testify-based tests.
- **Structure:** 1 source module (`app.go`), 1 test file (`app_test.go`, 11 tests).
- **Interfaces:** 7 HTTP routes (6 CRUD + health), all under an `/api` group; one `books` table.
- **Notable:** Routes served at `/api/*` while spec/tests use root paths; `year`+`isbn` are
  required beyond the spec's title/author; explicit empty-field checks are dead code after
  gin `required` binding.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
