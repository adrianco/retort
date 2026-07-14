# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.py | FastAPI app, SQLite persistence, all route handlers | `app`, `init_db()`, `get_book_by_id()`, `get_books()` |
| tests.py | Pytest integration tests via `TestClient` | 11 test functions |
| test_api.py | Standalone smoke-test script (runnable end-to-end walk) | `test_all_endpoints()` |
| README.md | Setup, run, and usage documentation | — |
| books.db | SQLite database file (created/committed by run) | — |
