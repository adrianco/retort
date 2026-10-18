# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.m | Reads `PORT`/`BOOKS_DB_PATH` env vars, wires store→API→server, starts listening | `main()` |
| src/BookStore.{h,m} | SQLite persistence via prepared statements + parameter binding | `BookStore`, `-initWithPath:error:`, `-createBookWithFields:`, `-bookWithID:`, `-booksWithAuthor:`, `-updateBookWithID:fields:`, `-deleteBookWithID:` |
| src/BookAPI.{h,m} | Routing, request validation, status-code selection; no socket code | `BookAPI`, `-handleMethod:path:query:body:`, `APIResponse` |
| src/HTTPServer.{h,m} | HTTP/1.1 parsing + response writing over POSIX sockets | `HTTPServer`, `-listenOnPort:error:`, `-serve`, `port` |
| tests/test_main.m | Self-contained test harness (no XCTest) for store, router, and end-to-end socket | `main()`, 6 test functions |
| Makefile | Build/test/run targets (`clang -fobjc-arc`, `-framework Foundation -lsqlite3`) | `all`, `test`, `run`, `clean` |
