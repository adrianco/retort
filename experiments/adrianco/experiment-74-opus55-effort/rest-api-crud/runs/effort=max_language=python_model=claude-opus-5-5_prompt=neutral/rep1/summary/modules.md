# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask app factory, routes, JSON error handling, entry point | `create_app()`, `main()`, `api` (Blueprint) |
| db.py | SQLite connection handling, schema, CRUD queries | `init_app()`, `connect()`, `list_books()`, `get_book()`, `create_book()`, `update_book()`, `delete_book()`, `ping()` |
| validation.py | Request payload validation (title/author/year/isbn) | `validate_book()`, `ValidationError` |
| tests/conftest.py | Shared pytest fixtures | `app`, `client`, `add_book` |
| tests/test_api.py | HTTP-level API tests via Flask test client | 20 test functions (75 cases w/ parametrization across the suite) |
| tests/test_validation.py | Unit tests for payload rules | 11 test functions |
