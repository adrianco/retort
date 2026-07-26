# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| bookapi/__init__.py | Application factory; wires config, DB, error handlers, blueprint | `create_app()` |
| bookapi/db.py | SQLite connection management + schema bootstrap | `connect()`, `get_db()`, `close_db()`, `init_db()`, `init_app()` |
| bookapi/repository.py | Data-access layer for the `books` table | `create()`, `get()`, `list_books()`, `update()`, `delete()` |
| bookapi/routes.py | HTTP endpoint handlers (Flask blueprint) | `bp`, `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| bookapi/validation.py | Flask-free request-payload validation | `validate_new_book()`, `validate_book_update()`, `validate_positive_int()`, `ValidationError` |
| bookapi/errors.py | JSON error handlers for validation/HTTP/unexpected errors | `register_error_handlers()` |
| run.py | Dev entry point that builds the app and runs it | `main()` |
| tests/conftest.py | Pytest fixtures (throwaway per-test DB, client) | fixtures |
| tests/test_books_crud.py | CRUD integration tests | 216 lines of test functions |
| tests/test_validation.py | Validation integration tests | test functions |
| tests/test_validation_unit.py | Validator unit tests | test functions |
| tests/test_listing.py | List/filter/pagination tests | test functions |
| tests/test_errors_and_persistence.py | Error-shape + persistence tests | test functions |
| tests/test_health.py | Health-check test | test functions |
| tests/sample_data.py | Shared fixture data | helpers |

58 test functions across 7 test modules.
