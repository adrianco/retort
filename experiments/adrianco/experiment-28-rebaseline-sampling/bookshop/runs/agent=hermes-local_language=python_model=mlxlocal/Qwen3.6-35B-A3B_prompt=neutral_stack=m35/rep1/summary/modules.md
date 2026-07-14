# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite storage, route handlers | `app`, `get_db()`, `init_db()`, `health()`, `create_book()`, `list_books()`, `get_book()`, `update_book()`, `delete_book()` |
| test_app.py | Pytest integration tests via Flask test client | 16 test functions across 6 test classes |
| requirements.txt | Dependencies | `flask>=3.0`, `pytest>=7.0` |
| README.md | Setup, run, and API usage docs | — |
