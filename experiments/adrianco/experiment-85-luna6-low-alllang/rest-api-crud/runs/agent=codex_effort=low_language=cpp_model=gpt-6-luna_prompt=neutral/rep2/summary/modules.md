# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| book_api.hpp | Public interface: request/response structs + `BookApi` class | `HttpRequest`, `HttpResponse`, `BookApi`, `reason_phrase()` |
| book_api.cpp | JSON parse/encode, validation, SQLite persistence, route dispatch | `BookApi::handle()`, `BookApi::BookApi()` |
| main.cpp | POSIX-socket HTTP server wrapping `BookApi` | `main()`, `serve_client()` |
| tests.cpp | In-process integration test exercising every route | `main()` (9 assertions) |
| CMakeLists.txt | Build: `book_api` lib, `book_server` exe, CTest `book_api_tests` | — |
