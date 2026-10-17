# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: config from env, starts `http.Server`, graceful shutdown | `main()`, `envOr()` |
| book.go | Book domain type + input validation (required fields, year range, ISBN checksum) | `Book`, `BookInput`, `Validate()`, `Normalize()`, `validISBN()` |
| store.go | SQLite persistence layer (CRUD + schema) | `Store`, `OpenStore()`, `Create/Get/List/Update/Delete`, `Ping` |
| handlers.go | HTTP router + handlers, JSON encode/decode, error responses | `NewServer()`, `handler`, `createBook/listBooks/getBook/updateBook/deleteBook/health` |
| server_test.go | API + unit integration tests (in-memory and on-disk SQLite) | 10 test functions |
