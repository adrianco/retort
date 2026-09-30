# Summary: effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral · rep 1

- **Shape:** Go standard-library `net/http` CRUD REST API with SQLite persistence via `database/sql` + pure-Go `modernc.org/sqlite`
- **Structure:** 2 source modules (`main.go`, `store.go`), 1 test file (`main_test.go`, 4 test functions)
- **Interfaces:** 6 HTTP routes / 0 CLI commands / 0 exported library functions (single `package main`)
- **Notable:** No web framework — Go 1.22 method-pattern `ServeMux`; CGO-free SQLite driver; single-connection pool so `:memory:` works in tests; 395 lines of Go in total

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
