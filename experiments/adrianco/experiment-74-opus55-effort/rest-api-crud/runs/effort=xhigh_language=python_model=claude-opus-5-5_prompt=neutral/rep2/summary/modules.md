# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books_api/__init__.py | Package facade; re-exports the public API | `BooksApp`, `BookRepository`, `Response`, `ValidationError`, `create_server`, `main`, `validate_book` |
| books_api/app.py | Transport-independent routing + request handling | `BooksApp`, `BooksApp.handle()`, `Response`, `Request`, `HTTPError` |
| books_api/db.py | SQLite persistence for books | `BookRepository` (`create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `ping`) |
| books_api/validation.py | Payload validation + normalisation | `validate_book()`, `ValidationError` |
| books_api/server.py | `http.server` transport + CLI entry point | `BooksHTTPServer`, `BooksRequestHandler`, `create_server()`, `main()`, `build_parser()` |
| books_api/__main__.py | `python -m books_api` shim | (module `__main__`) |
| tests/conftest.py | Pytest fixtures (`repo`, `app`, `call`, `create`) | 4 fixtures + `Result` NamedTuple |
| tests/samples.py | Shared sample book fixtures | `ORWELL`, `HUXLEY`, `ANIMAL_FARM` |
| tests/test_api.py | End-to-end API tests through `BooksApp.handle` | 26 test functions |
| tests/test_repository.py | `BookRepository` unit tests | 15 test functions |
| tests/test_validation.py | `validate_book` unit tests | 16 test functions |
| tests/test_server.py | HTTP transport / framing tests over a live socket | 13 test functions |
