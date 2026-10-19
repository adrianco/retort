# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite persistence, all route handlers | `app`, `init_db()`, `get_db()`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health` |
| tests/test_app.py | unittest-based API integration tests via Flask test client | `BookAPITestCase` (9 test methods) |
| README.md | Setup and run instructions, endpoint table, example curl requests | — |
