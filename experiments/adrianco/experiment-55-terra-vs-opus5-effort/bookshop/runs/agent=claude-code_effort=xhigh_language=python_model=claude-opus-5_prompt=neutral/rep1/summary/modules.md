# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| bookapi/__init__.py | Flask app factory; wires DB, error handlers, blueprint | `create_app()` |
| bookapi/routes.py | HTTP endpoints for the book collection | `bp`, route handlers (`create_book`, `list_books`, `get_book`, `replace_book`, `update_book`, `delete_book`, `health`, `index`) |
| bookapi/repository.py | SQL for the `books` table; returns plain dicts | `create_book`, `get_book`, `list_books`, `count_books`, `update_book`, `delete_book` |
| bookapi/validation.py | Input validation for book payloads and pagination | `validate_book`, `validate_book_patch`, `validate_pagination` |
| bookapi/db.py | SQLite connection management + schema init | `get_db`, `connect`, `init_db`, `init_app`, `init_db_command` |
| bookapi/errors.py | API error types + JSON error handlers | `ApiError`, `ValidationError`, `NotFoundError`, `ConflictError`, `register_error_handlers` |
| wsgi.py | WSGI entry point | `app` |
| tests/conftest.py | Shared fixtures (fresh app + SQLite file per test) | `app`, `client`, `create_book` fixtures |
| tests/test_books_crud.py | CRUD + filter + pagination integration tests | 20 test functions |
| tests/test_validation.py | Validation-layer tests | 24 test functions |
| tests/test_errors_and_storage.py | Error-handler + storage/timestamp tests | 9 test functions |
| tests/test_health.py | Health + service-index tests | 4 test functions |
