# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookStore.h/.m | SQLite-backed, thread-safe persistence for books | `BookStore`, `-initWithPath:error:`, `-createBookWithTitle:...`, `-booksFilteredByAuthor:`, `-bookWithID:`, `-updateBookWithID:...`, `-deleteBookWithID:`, `-isHealthy` |
| src/BooksAPI.h/.m | Transport-independent request router + JSON responses/validation | `BooksAPI`, `-handleMethod:target:body:`, `APIResponse`, `-validatedFieldsFromBody:failure:` |
| src/HTTPServer.h/.m | Minimal HTTP/1.1 server over BSD sockets (GCD concurrency) | `HTTPServer`, `-initWithAPI:`, `-startOnPort:error:`, `-stop` |
| src/main.m | Process entry point; wires store→API→server, reads PORT/DB_PATH env | `main` |
| tests/test_main.m | Self-contained test runner (no XCTest) | 8 test functions, `main` |
