# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| book_api.hpp | Public interface: `HttpResponse`, `BookApi` class, `reason_phrase` | `BookApi`, `HttpResponse`, `reason_phrase()` |
| book_api.cpp | Request routing, SQLite persistence, hand-rolled JSON parse/emit, URL decode/validation | `BookApi::handle()`, `BookApi::BookApi()`, `reason_phrase()` |
| main.cpp | POSIX TCP HTTP server loop wiring sockets to `BookApi::handle` | `main()` |
| tests.cpp | Assertion-based integration test driver over `BookApi` (`:memory:` DB) | `main()` (9 assertions) |
| CMakeLists.txt | Build: `book_api` lib, `book_server` exe, `book_api_tests` + CTest | — |
| README.md | Setup/build/run instructions, endpoint list | — |
