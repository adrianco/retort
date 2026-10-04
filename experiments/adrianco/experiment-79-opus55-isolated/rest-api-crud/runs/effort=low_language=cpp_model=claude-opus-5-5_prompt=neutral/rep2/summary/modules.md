# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.cpp | Process entry: reads HOST/PORT/DB_PATH env, wires store→server, blocks signals for graceful shutdown | `main()` |
| src/app.hpp | Transport-independent request/response types and routing contract | `Request`, `Response`, `handle_request()`, `book_to_json()` |
| src/app.cpp | Route dispatch, payload parsing/validation, id parsing, JSON serialization of books | `handle_request()`, `book_to_json()` |
| src/store.hpp | SQLite-backed persistence interface and `Book` model | `Book`, `BookStore` |
| src/store.cpp | SQLite CRUD via RAII prepared statements, mutex-guarded, schema init + author index | `BookStore::{create,list,get,update,remove}` |
| src/http_server.hpp | Blocking HTTP/1.1 server (thread-per-connection) + URL decode | `HttpServer`, `url_decode()` |
| src/http_server.cpp | Socket accept loop, request parsing, Content-Length/limit handling, response writing | `HttpServer::{listen,run,stop,serve}` |
| src/json.hpp | Header-only minimal JSON value, parser, and string escaping | `json::Value`, `json::parse()`, `json::quote()` |
| tests/test_main.cpp | Integration tests over `handle_request` and a real TCP socket | 12 test functions + `main()` runner |
