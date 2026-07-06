# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.py | FastAPI app factory and route handlers | `create_app()`, `app`, `BookIn`, `BookOut` |
| db.py | SQLite persistence layer (schema + CRUD) | `Database`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| test_books.py | BDD-style integration tests | 12 test functions, `client` fixture |
| requirements.txt | Python dependencies | fastapi, uvicorn, httpx, pytest |
| README.md | Setup, run, examples, status-code table | — |
