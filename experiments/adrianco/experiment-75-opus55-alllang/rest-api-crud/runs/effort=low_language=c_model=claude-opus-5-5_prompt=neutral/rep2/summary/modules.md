# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/books.h | Public interface: response type + open/handle API | `response_t`, `books_open`, `books_handle` |
| src/books.c | JSON parse/emit, validation, SQLite CRUD, request routing | `books_open`, `books_handle` (helpers: `parse_book`, `validate`, `list_books`, `write_book`, `delete_book`, `get_one`) |
| src/server.c | HTTP/1.1 socket server, request framing, response writing | `main`, `serve`, `reply` |
| tests/test_books.c | In-memory unit/integration tests over `books_handle` | `main`, 5 test functions, 19 assertions |
| tests/http_test.sh | End-to-end curl test against a live server | shell script |
| Makefile | Build + test targets | `all`, `test`, `clean` |
