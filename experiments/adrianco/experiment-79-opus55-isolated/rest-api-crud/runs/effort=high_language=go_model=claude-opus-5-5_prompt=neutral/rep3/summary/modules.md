# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Flags, server start-up, graceful shutdown | `main()`, `run()`, `envOr()` |
| store.go | SQLite schema and CRUD queries | `Book`, `Store`, `OpenStore()`, `ErrNotFound` |
| handlers.go | Routing, request decoding, validation, JSON responses | `Server`, `NewServer()`, `(*Server).Routes()` |
| handlers_test.go | End-to-end tests of the HTTP API | 7 test functions |
| store_test.go | Tests of the persistence layer | 5 test functions |
