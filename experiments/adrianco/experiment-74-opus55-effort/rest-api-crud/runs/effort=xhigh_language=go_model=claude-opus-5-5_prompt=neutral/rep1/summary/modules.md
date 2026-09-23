# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entry, flag/env config, HTTP server lifecycle + graceful shutdown | `main`, `run`, `defaultAddr` |
| book.go | Book/BookInput types, normalization, validation, ISBN format check | `Book`, `BookInput`, `Validate`, `Normalize`, `validISBNFormat` |
| store.go | SQLite persistence layer (schema, CRUD, author filter) | `Store`, `OpenStore`, `Create`, `List`, `Get`, `Update`, `Delete` |
| handlers.go | HTTP routing, request decoding, JSON responses, logging + panic-recovery middleware | `NewServer`, `Server`, handler methods, `writeJSON`, `decodeJSON` |
| book_test.go | Unit tests for normalization + validation | 2 test functions |
| store_test.go | Store CRUD / persistence / author-filter tests | 6 test functions |
| handlers_test.go | HTTP integration tests across all routes | 12 test functions |
| main_test.go | `defaultAddr` env-precedence test | 1 test function |
