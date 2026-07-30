# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Config, server startup, graceful shutdown | `main()`, `run()`, `envOr()` |
| api.go | Routing, request decode/validate, JSON responses, error mapping | `NewAPI()`, handlers (`health`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`) |
| store.go | SQLite schema, migration, and CRUD queries | `OpenStore()`, `Store.{Create,List,Get,Update,Delete,Ping,Close}`, `ErrNotFound`, `ErrDuplicateISBN` |
| book.go | `Book`/`BookInput` models, normalization, validation, ISBN check-digit logic | `Book`, `BookInput`, `Normalize()`, `Validate()`, `validISBN()` |
| api_test.go | End-to-end HTTP tests over a real in-memory SQLite store | 9 `Test*` functions, 13 subtests |
| book_test.go | Validation, normalization, and storage-layer unit tests | 6 `Test*` functions |
