# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| bookapi/__init__.py | Package exports | `BookApp`, `BookStore` |
| bookapi/app.py | WSGI app: routing, JSON parsing, error mapping | `BookApp`, `HttpError`, `ROUTES` |
| bookapi/store.py | SQLite persistence layer, thread-locked single connection | `BookStore` |
| bookapi/validation.py | Payload validation (title, author, year, ISBN-10/13 checksum) | `validate_book`, `is_valid_isbn`, `ValidationError` |
| bookapi/server.py | CLI entry point, threaded wsgiref server | `main`, `ThreadingWSGIServer` |
| bookapi/__main__.py | Enables `python -m bookapi` | `main` re-export |
| tests/test_api.py | Endpoint, validation, routing, persistence, and end-to-end tests | 35 test functions (46 cases with parametrization) |
