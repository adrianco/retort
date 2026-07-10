# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite persistence, all route handlers | `app`, `init_db()`, `get_db()`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health_check` |
| test_app.py | pytest integration tests against the Flask test client | 15 test functions across 7 test classes |
| README.md | Setup, run, API, and testing documentation | — |
