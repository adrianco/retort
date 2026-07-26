# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.py | FastAPI app, route handlers, error handlers | `app`, `create_book`, `list_books`, `get_book`, `replace_book`, `update_book`, `delete_book`, `health` |
| models.py | Pydantic request/response schemas + validation | `BookCreate`, `BookUpdate`, `BookPatch`, `Book`, `ErrorResponse`, `max_year` |
| database.py | SQLite persistence (stdlib `sqlite3`, no ORM) | `init_db`, `get_connection`, `create_book`, `list_books`, `get_book`, `replace_book`, `update_book`, `delete_book`, `ping` |
| conftest.py | Shared pytest fixtures | `db_path`, `client`, `conn`, `sample_book`, `create` |
| test_api.py | HTTP integration tests via TestClient | 43 test functions |
| test_database.py | Persistence + model unit tests | 20 test functions |
