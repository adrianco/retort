# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask app factory, route handlers, error handlers | `create_app()`, `bp`, `get_db()` |
| database.py | SQLite schema and CRUD queries | `connect()`, `init_db()`, `insert_book()`, `get_book()`, `list_books()`, `update_book()`, `delete_book()`, `ping()` |
| validation.py | Request payload and query-param validation | `parse_book()`, `parse_author_filter()`, `ValidationError` |
| tests/test_books_api.py | Endpoint tests via Flask test client against a real SQLite file | 29 test functions (several parametrized) |
| tests/test_validation.py | Unit tests for validation helpers, Flask-independent | 5 test functions |
| README.md | Setup, run, API reference, behavior notes | — |
| requirements.txt / requirements-dev.txt | Runtime (Flask) and dev (pytest) deps | — |
| pytest.ini | testpaths + pythonpath config | — |
