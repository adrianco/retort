# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books_api/__init__.py | Package exports | `BooksApp`, `create_app`, `BookRepository` |
| books_api/app.py | WSGI application, routing, request/response, HTTP error mapping | `BooksApp`, `create_app()`, `Request`, `Response`, `HTTPError` |
| books_api/models.py | Immutable data types shared across layers | `BookData`, `Book` |
| books_api/repository.py | SQLite-backed CRUD store | `BookRepository` (`create`, `list_books`, `get`, `update`, `delete`, `ping`) |
| books_api/validation.py | Payload validation for book fields | `validate_book()`, `ValidationError` |
| books_api/server.py | Multi-threaded stdlib WSGI HTTP server | `make_server()`, `ThreadingWSGIServer` |
| books_api/__main__.py | CLI entry point (`python -m books_api`) | `main()`, `parse_args()` |
| tests/conftest.py | pytest fixtures (in-memory repo, in-process client) | fixtures |
| tests/test_api.py | HTTP-level integration tests | 30 test functions |
| tests/test_repository.py | Repository unit tests | 10 test functions |
| tests/test_server.py | CLI / live-server tests | 6 test functions |
| tests/test_validation.py | Validation unit tests | 14 test functions |
