# Summary: hermes-local · go · stack=s2 · rep 1

- **Shape:** Go + Gin REST API with file-based SQLite (`go-sqlite3`) CRUD store.
- **Structure:** 1 source module (`app.go`), 1 test file (`app_test.go`), README.
- **Interfaces:** 6 HTTP routes (health + 5 book CRUD), 1 `books` table.
- **Notable:** Clean idiomatic handlers with pointer-based partial PUT; one dead helper (`scanBook`), unreachable `fmt.Println` after `r.Run`, and `isbn NOT NULL UNIQUE` unenforced at the validation layer.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
