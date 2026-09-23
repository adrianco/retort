# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| api.hpp | Public API surface: `Request`/`Response` structs, `BookApi` class, `url_decode` | `BookApi`, `Request`, `Response`, `url_decode` |
| api.cpp | Routing, hand-written JSON parse/serialize, input validation, SQLite storage | `BookApi::handle`, `BookApi::list/get/create/update/remove`, `url_decode` |
| main.cpp | Minimal single-threaded POSIX-socket HTTP/1.1 server driving `BookApi` | `main`, `serve` |
| tests.cpp | In-memory-SQLite tests via a `CHECK` macro | `main`, 5 `test_*` functions (28 checks) |
| CMakeLists.txt | Build: `bookapi` lib, `books_server` exe, `books_tests` exe + CTest | `books_server`, `books_tests` |
| README.md | Setup, build/test, run instructions and endpoint table | — |
