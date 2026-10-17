# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Entry point: flags, startup, graceful shutdown on SIGINT/SIGTERM | `main()`, `run()` |
| server.go | HTTP routes, handlers, JSON helpers, JSON-rewrite of 404/405 | `Server`, `NewServer()`, `Handler()` |
| store.go | SQLite persistence, schema migration, CRUD queries | `Store`, `OpenStore()`, `Create/Get/List/Update/Delete`, `ErrNotFound` |
| book.go | Book model, input validation, ISBN-10/13 check-digit validation | `Book`, `BookInput`, `Validate()`, `validISBN()` |
| server_test.go | End-to-end HTTP tests | 7 test functions |
| store_test.go | SQLite CRUD / filter / persistence tests | 4 test functions |
| book_test.go | Validation and ISBN unit tests | 3 test functions |
