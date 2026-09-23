# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Config, HTTP server, graceful shutdown | `main()`, `envOr()` |
| handlers.go | Routes, request decode, validation, JSON output | `NewServer()`, `Server`, `BookInput`, `validISBN()` |
| store.go | `Store` interface + SQLite implementation | `Store`, `SQLiteStore`, `OpenSQLiteStore()`, `Book`, `ErrNotFound` |
| handlers_test.go | Integration + unit tests | 15 test functions |
