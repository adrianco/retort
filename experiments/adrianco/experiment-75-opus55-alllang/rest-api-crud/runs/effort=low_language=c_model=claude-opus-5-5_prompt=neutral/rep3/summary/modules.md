# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books.h | Public API of the transport-independent request handler | `response_t`, `books_init_db()`, `books_handle()` |
| src/books.c | Routing, JSON parse/emit, validation, SQLite access | `books_init_db()`, `books_handle()` |
| src/main.c | Single-threaded HTTP/1.1 socket server | `main()`, `handle_conn()`, `reply()` |
| tests/test_books.c | Integration tests calling `books_handle()` against an in-memory DB | `main()`, 5 `test_*` functions |
| Makefile | Build `books_server`; build+run sanitized `test_books` | `all`, `test` |
| README.md | Setup, run, endpoint reference | — |
