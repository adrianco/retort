# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app/main.py | FastAPI app + route handlers | `app`, `get_db()`, `create_book()`, `list_books()`, `get_book()`, `update_book()`, `delete_book()`, `health_check()` |
| app/database.py | SQLite connection + schema init | `get_connection()`, `init_db()`, `DEFAULT_DB_PATH` |
| app/schemas.py | Pydantic request/response models + validation | `BookBase`, `BookCreate`, `BookUpdate`, `BookResponse` |
| app/__init__.py | Package marker | (empty) |
| tests/conftest.py | Pytest fixture: TestClient over a per-test temp SQLite DB | `client` fixture |
| tests/test_books.py | BDD integration tests for CRUD + filter + validation | 11 test functions |
| tests/test_health.py | BDD integration test for /health | 1 test function |
| tests/__init__.py | Package marker | (empty) |
