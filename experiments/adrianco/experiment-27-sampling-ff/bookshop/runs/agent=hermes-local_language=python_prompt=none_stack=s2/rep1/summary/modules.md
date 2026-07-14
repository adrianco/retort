# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, route handlers, and raw sqlite3 data access | `app`, `get_db()`, `init_db()`, `close_db()`, `row_to_dict()`, `health()`, `create_book()`, `list_books()`, `get_book()`, `update_book()`, `delete_book()` |
| test_app.py | Pytest integration tests against the Flask test client | 13 test functions across 6 test classes; fixtures `clean_db`, `client` |
