# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, book CRUD route handlers, SQLite access | `app`, `get_db()`, `init_db()`, `book_to_dict()`, `health_check()`, `create_book()`, `list_books()`, `get_book()`, `update_book()`, `delete_book()` |
| test_app.py | Pytest integration tests against a temp-DB test client | `client` fixture, 18 test functions |
