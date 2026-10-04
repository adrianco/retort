# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Server bootstrap, env config, graceful shutdown | `main()`, `getenv()` |
| handlers.go | HTTP router, request decoding/validation, JSON responses | `NewHandler()`, `Server`, `decodeBook()` |
| store.go | SQLite persistence and CRUD queries | `NewStore()`, `Store`, `Book`, `ErrNotFound` |
| handlers_test.go | HTTP integration tests | 12 test functions |
