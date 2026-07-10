# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite backend, all route handlers | `app`, `get_db()`, `init_db()`, `health_check()`, `create_book()`, `list_books()`, `get_book()`, `update_book()`, `delete_book()` |
| test_app.py | Integration tests via Flask test client | 18 test functions, `test_db` fixture |
| requirements.txt | Dependency pins | flask>=3.0, pytest>=7.0 |
| README.md | Setup, run, and endpoint documentation | — |
