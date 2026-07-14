# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite connection management, and all route handlers | `app`, `get_db()`, `init_db()`, `health_check()`, `create_book()`, `list_books()`, `get_book()`, `update_book()`, `delete_book()` |
| test_app.py | BDD-style (Given-When-Then) API integration tests via the Flask test client | 19 test functions across 6 `Test*` feature classes |
| README.md | Setup, run, and API reference documentation | — |
