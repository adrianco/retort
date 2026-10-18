# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/book.hpp | Book model, BookInput, ValidationError/DuplicateIsbnError, JSON decls | `Book`, `BookInput`, `ValidationError`, `parse_book_input`, `to_json` |
| src/book.cpp | Input validation (required/trimmed title+author, year range, ISBN shape) and JSON serialization | `parse_book_input`, `to_json` |
| src/repository.hpp | SQLite-backed repository interface | `BookRepository` |
| src/repository.cpp | SQLite storage: schema, CRUD, isbn-unique handling, ping | `insert`, `find`, `list`, `update`, `remove`, `ping` |
| src/api.hpp | Request/Response types and request handler decl | `Request`, `Response`, `handle_request` |
| src/api.cpp | Routing/dispatch, query parsing, id parsing, error mapping | `handle_request`, `dispatch` |
| src/main.cpp | Blocking Boost.Beast HTTP server wrapping the core handler | `main` |
| tests/api_tests.cpp | Boost.Test integration tests against in-memory DB | 9 test cases |
