# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| bookapi/__init__.py | Package exports | `create_server`, `BookStore` |
| bookapi/__main__.py | CLI entry point (`python -m bookapi`) | `main()` |
| bookapi/http_app.py | HTTP server, routing, JSON handling | `create_server()`, `BookAPIServer`, `BookAPIHandler` |
| bookapi/store.py | SQLite-backed book repository | `BookStore` |
| bookapi/validation.py | Book payload validation (incl. ISBN checksums) | `validate_book()`, `ValidationError` |
| tests/test_api.py | HTTP integration tests (live server) | 15 test functions (some parametrized) |
| tests/test_store.py | SQLite persistence tests | 5 test functions |
| tests/test_validation.py | Validation unit tests | 6 test functions (parametrized) |
