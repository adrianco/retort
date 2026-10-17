# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: opens store, builds server, runs HTTP with graceful shutdown | `main`, `getenv` |
| book.go | Book/BookInput domain types, validation, ISBN shape check | `Book`, `BookInput`, `Validate`, `Normalize`, `validISBN` |
| store.go | SQLite persistence layer (CRUD + schema + sentinels) | `Store`, `OpenStore`, `Create`, `Get`, `List`, `Update`, `Delete`, `Ping` |
| handlers.go | HTTP routing, request decoding, status-code mapping | `Server`, `NewServer`, `handle*`, `decodeBookInput`, `writeJSON` |
| book_test.go | Validation/normalization unit tests | 2 test functions |
| store_test.go | Store persistence/sentinel/uniqueness tests | 4 test functions |
| handlers_test.go | HTTP integration tests (CRUD, filter, validation, errors) | 9 test functions |
