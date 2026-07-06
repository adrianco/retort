# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.py | FastAPI app, Pydantic schemas, route handlers | `app`, `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `get_db_path`, `lifespan` |
| database.py | SQLite data-access layer (raw sqlite3, no ORM) | `init_db`, `get_connection`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| test_main.py | pytest integration tests via `TestClient` | 9 test functions |
| README.md | Setup / run / test docs | — |
| requirements.txt | Runtime + test dependencies | — |
