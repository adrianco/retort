# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bookapi/__init__.py | Package root; re-exports public classes | `BookApp`, `BookStore` |
| src/bookapi/app.py | WSGI app: routing, JSON rendering, error handling | `BookApp`, `ApiError`, `Response` |
| src/bookapi/db.py | SQLite-backed book storage | `BookStore` |
| src/bookapi/validation.py | Input validation for book payloads | `validate_book()` |
| src/bookapi/server.py | Stdlib WSGI server wiring | `create_server()`, `ThreadingWSGIServer`, `QuietHandler` |
| src/bookapi/__main__.py | CLI entry point (`python -m bookapi`) | `main()` |
| tests/conftest.py | Pytest fixtures + in-process WSGI test client | `store`, `client`, `make_book`, `Client`, `Response` |
| tests/test_api.py | End-to-end HTTP/route tests | 41 test functions |
| tests/test_cli.py | CLI entry-point test | 1 test function |
| tests/test_server.py | Server construction/wiring tests | 3 test functions |
| tests/test_store.py | BookStore storage-layer tests | 8 test functions |
| tests/test_validation.py | validate_book unit tests | 9 test functions |
