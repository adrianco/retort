# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app/main.py | FastAPI app + route handlers, lifespan DB init | `app`, `health_check`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| app/database.py | SQLite connection + schema init (env-overridable path) | `get_connection()`, `init_db()`, `get_db_path()` |
| app/crud.py | SQL data-access operations | `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| app/schemas.py | Pydantic request/response models | `BookCreate`, `BookUpdate`, `Book` |
| app/__init__.py | Package marker | (empty) |
| tests/conftest.py | Pytest fixture: isolated temp-DB TestClient | `client` fixture |
| tests/test_create_book.py | Create-endpoint tests | 3 test functions |
| tests/test_list_books.py | List + author-filter tests | 3 test functions |
| tests/test_get_book.py | Get-by-id tests | 2 test functions |
| tests/test_update_book.py | Update-endpoint tests | 3 test functions |
| tests/test_delete_book.py | Delete-endpoint tests | 2 test functions |
| tests/test_health.py | Health-check test | 1 test function |
