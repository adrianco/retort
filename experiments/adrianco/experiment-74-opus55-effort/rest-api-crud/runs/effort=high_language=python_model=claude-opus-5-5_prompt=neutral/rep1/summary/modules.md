# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books_api/app.py | WSGI app: routing, request parsing, HTTP handlers | `BooksApp`, `create_app()`, `HttpError` |
| books_api/db.py | Thread-safe SQLite CRUD repository | `BookRepository`, `DuplicateIsbnError` |
| books_api/validation.py | Book payload validation/normalisation | `validate_book()` |
| books_api/__main__.py | Threaded WSGI server + CLI (`--host/--port/--db`) | `main()`, `make_books_server()`, `ThreadingWSGIServer` |
| books_api/__init__.py | Package exports | `BooksApp`, `BookRepository`, `create_app` |
| tests/conftest.py | In-process WSGI client + fixtures | `WsgiClient`, `client`, `app`, `sample_book` |
| tests/test_api.py | Endpoint/validation tests (in-process) | 18 test functions (several parametrized) |
| tests/test_integration.py | Real-HTTP end-to-end tests over file-backed SQLite | 3 test functions |
