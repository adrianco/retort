# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/book_api.hpp | Public interface: `Response`, `JsonValue`, `BookApi` class, JSON/URL helpers | `BookApi`, `parse_json_object()`, `json_escape()`, `url_decode()` |
| src/book_api.cpp | Request routing, SQLite CRUD, hand-rolled JSON parser/serializer, validation | `BookApi::handle()`, `create/get/list/update/remove`, `parse_json_object()` |
| src/main.cpp | Single-threaded POSIX-socket HTTP/1.1 server wrapping `BookApi` | `main()`, `serve()` |
| tests/test_api.cpp | Integration tests driving `BookApi::handle()` against an in-memory DB | `main()` — 25 `CHECK` assertions |
