# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.cpp | Process entry: reads PORT/HOST/DB_PATH env, opens store, starts server | `main()` |
| src/app.hpp / src/app.cpp | Request routing and handler logic; book↔JSON mapping; validation | `Request`, `Response`, `handleRequest()`, `bookToJson()` |
| src/store.hpp / src/store.cpp | SQLite persistence layer (schema, CRUD, author index, mutex) | `Book`, `BookStore` (`create`/`list`/`get`/`update`/`remove`) |
| src/server.hpp / src/server.cpp | POSIX-socket HTTP/1.1 server, one thread per connection | `HttpServer` (`listen`/`serve`/`stop`) |
| src/json.hpp / src/json.cpp | Hand-written JSON parser + string escaper | `json::Value`, `json::parse()`, `json::quote()` |
| tests/test_main.cpp | 11 handler-level + end-to-end TCP tests | 11 test functions, `main()` |
| CMakeLists.txt | Build config; links SQLite3 + Threads | `book_core`, `book_api`, `book_tests` targets |
