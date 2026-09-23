# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/json.hpp | Minimal JSON value/object types + declarations | `json::Value`, `json::Object`, `escape`, `parse_object` |
| src/json.cpp | Flat-object JSON parser and string escaper | `json::escape`, `json::parse_object` |
| src/book_store.hpp | SQLite-backed repository interface + `Book` struct | `Book`, `BookStore` |
| src/book_store.cpp | CRUD over an SQLite `books` table (prepared stmts) | `BookStore::create/list/get/update/remove/healthy` |
| src/api.hpp | Transport-independent request/response types + router | `Request`, `Response`, `Api`, `url_decode`, `parse_target` |
| src/api.cpp | REST routing, validation, JSON serialization | `Api::handle`, `url_decode`, `parse_target` |
| src/main.cpp | POSIX-socket HTTP/1.1 server wiring the API | `main`, `serve`, `respond` |
| tests/test_api.cpp | Self-contained assertion-based API tests | 7 `test_*` functions, `main` |

Build artifacts (`books_server`, `test_api`, `*.db`) are gitignored and excluded.
