# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.m | Entry point: reads env config, opens the store, starts the server, runs the dispatch loop | `main()` |
| src/HTTPServer.h/.m | Minimal HTTP/1.1 server on BSD sockets; one request per connection, dispatches to `BooksAPI` | `HTTPServer` (`initWithAPI:`, `startOnHost:port:error:`, `stop`) |
| src/BooksAPI.h/.m | Transport-independent request router: parsing, validation, JSON responses, status codes | `BooksAPI` (`handleMethod:path:query:body:`), `APIResponse` |
| src/BookStore.h/.m | SQLite persistence layer with prepared statements | `BookStore` (`initWithPath:error:`, `createBook:error:`, `listBooksWithAuthor:error:`, `bookWithID:error:`, `updateBook:fields:error:`, `deleteBook:error:`) |
| tests/test_main.m | Self-contained test runner: unit tests over an in-memory DB plus real HTTP integration tests | 11 test functions, `main()` |
