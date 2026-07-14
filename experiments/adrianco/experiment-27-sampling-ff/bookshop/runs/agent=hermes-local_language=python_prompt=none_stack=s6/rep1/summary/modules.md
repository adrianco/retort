# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite persistence, route handlers, validation | `app`, `init_db()`, `get_db()`, `validate_book_data()`, `health_check`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| test_app.py | pytest integration tests via Flask test client | 17 test functions across 6 test classes + integration |
| requirements.txt | Runtime/test dependencies | flask, pytest |
| README.md | Setup, run, and API usage documentation | — |
