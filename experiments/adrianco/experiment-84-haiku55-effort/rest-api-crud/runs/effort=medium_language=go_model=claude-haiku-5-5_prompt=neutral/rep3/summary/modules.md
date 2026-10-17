# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry point: opens the store, wires the HTTP server, graceful shutdown | `main`, `envOr` |
| handlers.go | HTTP handler: routing, request decoding/validation, JSON responses, status mapping | `NewServer`, `handler`, route methods |
| store.go | SQLite persistence layer (pure-Go driver) and CRUD data access | `OpenStore`, `Store`, `Create/Get/List/Update/Delete` |
| book.go | Domain types, input normalization, validation, ISBN checksum logic | `Book`, `BookInput`, `validate`, `isValidISBN` |
| api_test.go | HTTP integration tests through the full handler stack | 11 test functions |
| store_test.go | Store-level persistence/uniqueness tests | 3 test functions |
| book_test.go | Validation and ISBN unit tests | 3 test functions |
