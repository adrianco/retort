# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.m | Process entry: opens the DB, wires store→API→server, serves forever | `main()` |
| src/Book.h/.m | Book model, JSON (de)serialization and validation | `Book`, `+bookFromDictionary:error:`, `-jsonDictionary` |
| src/BookStore.h/.m | SQLite persistence layer (CRUD + author filter) | `BookStore`, `-initWithPath:error:`, `-insertBook:`, `-bookWithID:`, `-booksByAuthor:`, `-updateBook:`, `-deleteBookWithID:` |
| src/BookAPI.h/.m | Request router / REST handlers over a `BookStore` | `BookAPI`, `-handleRequest:` |
| src/HTTPMessage.h/.m | HTTP request/response value objects + JSON response builders | `HTTPRequest`, `HTTPResponse`, `+responseWithStatus:json:`, `+errorResponseWithStatus:message:` |
| src/HTTPServer.h/.m | BSD-socket HTTP/1.1 server (parse request, dispatch handler, write response) | `HTTPServer`, `-startWithError:`, `-serveForever` |
| tests/main.m | Custom test runner with 8 unit/integration test cases | `main()`, 8 `TestCase` functions |
