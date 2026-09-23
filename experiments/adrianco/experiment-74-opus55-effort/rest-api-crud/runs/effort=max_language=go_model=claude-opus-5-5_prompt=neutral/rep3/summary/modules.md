# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry point; flag/env config, DB open, graceful HTTP serve | `main()`, `run()`, `serve()` |
| server.go | HTTP handler wiring, middleware, JSON/error writers | `NewHandler()`, `writeJSON()`, `server.writeError` |
| handlers.go | Route handlers, request decoding & id parsing | `server.handleHealth/List/Create/Get/Update/Delete`, `decodeJSON()` |
| store.go | SQLite persistence layer (CRUD, schema, filtering) | `OpenStore()`, `Store.Create/Get/List/Update/Delete` |
| book.go | Domain model, input normalization & validation | `Book`, `BookInput`, `Validate()`, `Normalize()`, `ValidationError` |
| book_test.go | Model/validation unit tests | 3 test functions |
| store_test.go | Store persistence tests | 5 test functions |
| handlers_test.go | HTTP handler integration tests | 11 test functions |
| main_test.go | Server lifecycle (graceful shutdown) tests | 2 test functions |
