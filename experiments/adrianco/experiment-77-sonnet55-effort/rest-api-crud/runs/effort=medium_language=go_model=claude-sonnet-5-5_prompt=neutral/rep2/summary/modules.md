# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: opens store, reads `ADDR`/`DB_PATH` env, starts HTTP server | `main()`, `getenv()` |
| handlers.go | HTTP router and request handlers, JSON writing, ID parsing, body validation | `NewHandler()`, `api`, `writeJSON()`, `writeErr()`, `parseID()`, `decode()` |
| store.go | SQLite persistence layer and `Book` model | `Book`, `Store`, `NewStore()`, `Create()`, `List()`, `Get()`, `Update()`, `Delete()`, `errNotFound` |
| main_test.go | HTTP integration tests against an in-memory store | `TestHealth`, `TestCRUD`, `TestValidation`, `TestListAuthorFilter` (4 test functions) |

Non-source files present: `go.mod`, `go.sum`, `README.md` (skipped: harness artifacts, DB files).
