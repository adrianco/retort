# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Flag parsing, HTTP server lifecycle, graceful shutdown | `main()` |
| server.go | HTTP router, route handlers, JSON encode/decode, error mapping | `NewServer()`, `Server.ServeHTTP` |
| store.go | SQLite persistence (schema, CRUD, author filter, ISBN uniqueness) | `OpenStore()`, `Store.{Create,Get,List,Update,Delete,Ping,Close}` |
| book.go | Domain model, input validation, ISBN normalization | `Book`, `BookInput`, `BookInput.Validate`, `ErrNotFound`, `ErrISBNConflict` |
| server_test.go | HTTP integration tests via httptest | 7 test functions |
| book_test.go | Unit tests for validation and ISBN normalization | 2 test functions |
