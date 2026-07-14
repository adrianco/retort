# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite connection, all route handlers | `app`, `get_db()`, `init_db()`, `health()`, `create_book()`, `list_books()`, `get_book()`, `update_book()`, `delete_book()` |
| test_app.py | Pytest acceptance/integration tests | 17 test functions across 7 test classes |
| README.md | Setup, run, and API usage documentation | — |
| books.db | SQLite database (created automatically) | `books` table |
