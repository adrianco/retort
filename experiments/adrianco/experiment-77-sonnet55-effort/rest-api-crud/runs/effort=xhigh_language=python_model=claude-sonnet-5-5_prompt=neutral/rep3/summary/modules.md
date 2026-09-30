# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bookapi/__init__.py | Package root; builds a ready-to-serve WSGI app | `create_app()`, re-exports `BookApp`, `BookStore`, `ValidationError`, `validate_book` |
| src/bookapi/app.py | WSGI app: routing, dispatch, JSON request/response, HTTP error handling | `BookApp`, `HTTPError` |
| src/bookapi/store.py | SQLite-backed book persistence, thread-safe over one connection | `BookStore` |
| src/bookapi/validation.py | Input validation for book payloads | `validate_book()`, `ValidationError` |
| src/bookapi/__main__.py | `python -m bookapi` entry: arg parsing + threading WSGI server | `main()`, `ThreadingWSGIServer` |
| tests/conftest.py | Test fixtures and an in-process WSGI test client | `store`, `client`, `book_payload` fixtures; `Client` |
| tests/test_api.py | HTTP-level API integration tests (via in-process client) | 31 test functions |
| tests/test_server.py | End-to-end CRUD over a real HTTP socket | `test_full_crud_lifecycle_over_http` |
| tests/test_store.py | Unit tests for `BookStore` and `validate_book` | 10 test functions |
