# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite storage, route handlers, input validation | `app`, `get_db()`, `init_db()`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health_check` |
| test_app.py | pytest API integration tests | 18 test functions across 6 test classes |
| requirements.txt | Dependencies | flask>=3.0, pytest>=8.0 |
| README.md | Setup, run, and API docs | — |
