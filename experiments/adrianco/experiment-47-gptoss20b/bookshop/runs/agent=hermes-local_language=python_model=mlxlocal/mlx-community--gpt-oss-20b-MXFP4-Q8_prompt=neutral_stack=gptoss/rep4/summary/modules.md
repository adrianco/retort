# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.py | FastAPI app + route handlers, uvicorn entry | `app`, `get_db()`, `health()`, `create_book()`, `list_books()`, `get_book()`, `update_book()`, `delete_book()` |
| database.py | SQLAlchemy engine/session + declarative base (SQLite) | `engine`, `SessionLocal`, `Base` |
| models.py | SQLAlchemy ORM model | `Book` |
| schemas.py | Pydantic request/response schemas | `BookBase`, `BookCreate`, `BookUpdate`, `BookRead` |
| tests/conftest.py | Adds project root to sys.path for imports | (import shim) |
| tests/test_api.py | API integration tests via TestClient | 5 test functions |
