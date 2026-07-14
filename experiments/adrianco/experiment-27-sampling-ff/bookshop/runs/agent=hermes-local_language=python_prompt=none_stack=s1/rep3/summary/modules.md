# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite storage, route handlers | `app`, `get_db()`, `init_db()`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health` |
| test_app.py | pytest integration tests via Flask test client | 16 test methods across 6 classes |
