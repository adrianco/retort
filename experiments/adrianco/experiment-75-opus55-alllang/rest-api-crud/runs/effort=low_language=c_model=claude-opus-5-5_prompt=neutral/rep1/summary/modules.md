# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books.h | Public interface: `response_t`, DB init, request router | `books_init_db`, `books_handle`, `response_t` |
| src/books.c | Routing, JSON parse/emit, validation, SQLite access (transport-independent) | `books_handle`, `books_init_db` |
| src/server.c | HTTP/1.1 socket server, request parsing, `main()` | `main`, `handle_client` |
| tests/test_books.c | Endpoint tests against an in-memory DB | `main` + 5 `test_*` functions |
