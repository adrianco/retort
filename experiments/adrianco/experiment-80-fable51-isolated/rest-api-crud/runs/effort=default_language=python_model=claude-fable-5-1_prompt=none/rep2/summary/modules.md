# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI HTTP server, SQLite persistence, route handlers, validation | `create_app()`, `validate_book()`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health` |
| test_app.py | In-process WSGI integration tests | 12 test functions (one parametrized ×8) + `Client`/`Response` helpers |
