# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | FastAPI app, SQLite setup, route handlers | `app`, `init_db()`, `get_db()`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health_check` |
| tests/test_app.py | API integration tests via TestClient | 15 test functions |
| tests/__init__.py | Empty package marker | (none) |
| README.md | Setup and run instructions | (docs) |
