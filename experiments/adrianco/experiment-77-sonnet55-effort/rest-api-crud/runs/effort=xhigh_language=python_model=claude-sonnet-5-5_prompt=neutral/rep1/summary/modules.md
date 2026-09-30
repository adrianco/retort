# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bookapi/app.py | WSGI app: routing, request/response layer, error mapping, CRUD handlers | `BookApp`, `create_app()`, `ApiError`, `Request`, `Response` |
| src/bookapi/db.py | Thread-safe SQLite persistence for books | `BookRepository` (`create`, `get`, `list_books`, `update`, `delete`, `ping`) |
| src/bookapi/validation.py | Input validation for book payloads | `validate_book()` |
| src/bookapi/__main__.py | CLI entry: threaded stdlib WSGI server | `main()`, `ThreadingWSGIServer` |
| src/bookapi/__init__.py | Package marker | (none) |
| tests/conftest.py | Pytest fixtures (in-memory app/client harness) | fixtures |
| tests/test_api.py | End-to-end HTTP API tests | 43 test functions |
| tests/test_validation.py | Unit tests for `validate_book` | 8 test functions |
| tests/test_repository.py | Unit tests for `BookRepository` | 6 test functions |
| tests/test_server.py | `__main__` server / CLI tests | 3 test functions |
