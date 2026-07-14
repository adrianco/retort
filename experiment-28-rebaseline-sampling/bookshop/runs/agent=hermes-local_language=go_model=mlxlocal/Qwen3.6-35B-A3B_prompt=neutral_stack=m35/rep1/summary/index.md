# Summary: hermes-local · go · mlxlocal/Qwen3.6-35B-A3B · neutral · m35 · rep 1

- **Shape:** Go + Gin REST API with SQLite (mattn/go-sqlite3) persistence.
- **Structure:** 1 source module (`app.go`), 1 test file (`app_test.go`), 9 test cases.
- **Interfaces:** 6 HTTP routes (5 CRUD on `/books` + `/health`), 1 `books` table.
- **Notable:** Clean single-file implementation; package-level `db` global swapped for a temp DB in tests. Minor quirks — `year` defaults to `2000` when omitted, and PUT re-validates required fields.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
