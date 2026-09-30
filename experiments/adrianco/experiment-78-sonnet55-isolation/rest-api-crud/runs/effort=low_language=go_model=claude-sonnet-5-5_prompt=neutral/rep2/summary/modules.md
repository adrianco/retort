# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite persistence, all route handlers | `Book`, `Server`, `NewServer()`, `Handler()`, `main()` |
| main_test.go | httptest integration tests against an in-memory DB | `TestHealth`, `TestCRUD`, `TestValidation`, `TestListFilter` |

Non-source files: `go.mod`, `go.sum` (deps), `README.md` (docs).
