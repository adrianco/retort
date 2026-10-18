# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.m | Process entry: reads PORT/BOOKS_DB_PATH env, wires store+API+server | `main()` |
| src/Book.h / src/Book.m | Book model, validation, JSON (de)serialization, error domain | `Book`, `bookFromJSONObject:error:`, `JSONObject`, `BookError()` |
| src/BookStore.h / src/BookStore.m | SQLite-backed persistence (CRUD + ping) | `BookStore`, `initWithPath:error:`, `insertBook:`, `bookWithId:`, `booksByAuthor:`, `updateBook:`, `deleteBookWithId:`, `ping:` |
| src/BookAPI.h / src/BookAPI.m | Request router mapping HTTP verbs/paths to store operations | `BookAPI`, `initWithStore:`, `handleRequest:` |
| src/HTTP.h / src/HTTP.m | HTTP request/response value types + wire serialization | `HTTPRequest`, `HTTPResponse`, `HTTPRequestCreate()`, `jsonResponse:object:`, `errorResponse:message:`, `emptyResponse:`, `serialized` |
| src/HTTPServer.h / src/HTTPServer.m | Single-threaded BSD-socket HTTP/1.1 server (127.0.0.1) | `HTTPServer`, `initWithHandler:`, `listenOnPort:error:`, `serveForever`, `port` |
| tests/BookServiceTests.m | Custom CHECK-macro harness exercising model, store, routing, and a real socket | 8 test functions, `main()` |
