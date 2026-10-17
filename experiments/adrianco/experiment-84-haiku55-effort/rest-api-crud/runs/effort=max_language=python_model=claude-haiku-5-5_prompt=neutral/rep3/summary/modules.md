# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| bookapi/__init__.py | App factory; wires db, error handlers, blueprint, `/health` route | `create_app()`, `health()` |
| bookapi/books.py | HTTP routes for the `/books` collection (blueprint) | `bp`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| bookapi/db.py | SQLite connection per app context + schema creation | `get_db()`, `close_db()`, `init_app()`, `default_database_path()` |
| bookapi/repository.py | Parameterized SQL CRUD over the `books` table | `insert_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| bookapi/validation.py | Payload validation (required fields, year bounds, ISBN checksum) | `validate_book`, `validate_author_filter`, `normalize_isbn` |
| bookapi/errors.py | JSON error responses for `ApiError` and Werkzeug `HTTPException` | `ApiError`, `register_error_handlers()` |
| tests/conftest.py | pytest fixtures: app + test client on a temp SQLite file | `app`, `client` |
| tests/test_books_api.py | HTTP endpoint integration tests via Flask test client | 28 test functions |
| tests/test_validation.py | Unit tests for the validation module | 9 test functions |
