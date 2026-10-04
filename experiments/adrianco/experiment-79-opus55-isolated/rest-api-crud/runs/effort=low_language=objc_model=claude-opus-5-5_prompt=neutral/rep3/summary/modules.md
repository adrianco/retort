# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookStore.h/.m | SQLite-backed, thread-safe persistence for books | `BookStore` (`initWithPath:error:`, CRUD methods) |
| src/BookAPI.h/.m | Transport-independent request router, validation, status codes | `BookAPI` (`handleMethod:path:query:body:`), `APIResponse` |
| src/HTTPServer.h/.m | Minimal HTTP/1.1 server (one request per connection) over BSD sockets | `HTTPServer` (`startOnPort:error:`, `stop`) |
| src/main.m | Entry point: reads PORT/DB_PATH env, wires store→API→server | `main` |
| tests/test_main.m | API tests on in-memory DB + end-to-end HTTP tests | 11 test functions, 86 assertions |
