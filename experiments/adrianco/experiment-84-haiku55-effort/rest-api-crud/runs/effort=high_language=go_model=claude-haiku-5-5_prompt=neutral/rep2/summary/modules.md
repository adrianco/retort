# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Flags, startup, graceful shutdown | `main()`, `run()` |
| server.go | Routes, HTTP handlers, JSON helpers | `NewHandler()`, `server`, `writeJSON()` |
| book.go | Book model, normalization, ISBN-aware validation | `Book`, `BookFields`, `ValidationError`, `Validate()`, `Normalize()` |
| store.go | SQLite persistence and schema | `Store`, `OpenStore()`, `Create/Get/List/Update/Delete`, `ErrNotFound` |
| book_test.go | Validation + normalization unit tests | 3 test functions |
| store_test.go | Store tests against a real SQLite file | 4 test functions |
| server_test.go | HTTP integration tests across all endpoints | 9 test functions |
