# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bookapi/app.py | WSGI app: routing, request parsing, JSON error handling | `BookAPI`, `APIError` |
| src/bookapi/store.py | SQLite persistence for books | `BookStore` |
| src/bookapi/validation.py | Validate/normalise book payloads | `validate_book()` |
| src/bookapi/server.py | CLI entry point; threaded wsgiref server | `main()`, `create_server()` |
| src/bookapi/__main__.py | `python -m bookapi` shim | `main` |
| src/bookapi/__init__.py | Package marker | — |
| tests/test_api.py | End-to-end WSGI API tests | 33 test functions |
| tests/test_store.py | BookStore persistence tests | 3 test functions |
| tests/test_server.py | Server wiring test | 1 test function |
| tests/conftest.py | pytest fixtures (in-memory store, WSGI client) | fixtures |
