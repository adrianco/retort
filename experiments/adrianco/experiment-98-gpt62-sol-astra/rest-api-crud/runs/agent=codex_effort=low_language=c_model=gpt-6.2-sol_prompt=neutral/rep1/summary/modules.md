# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books.c | HTTP server, routing, CRUD handlers, validation, SQLite access | `main()`, `route()`, `books()`, `open_database()`, `reply()` |
| test_books.c | In-process C unit tests (includes books.c, stubs `evhttp_send_reply`) | `main()`, 5 `test_*` functions |
| test_books.py | End-to-end HTTP integration tests over a spawned server | `BookApiTests`, 5 `test_*` methods |
| Makefile | Build + test targets (`all`, `test`, `test-http`, `clean`) | `book-api`, `test-books` |
| README.md | Setup, run, endpoint, and test documentation | — |
