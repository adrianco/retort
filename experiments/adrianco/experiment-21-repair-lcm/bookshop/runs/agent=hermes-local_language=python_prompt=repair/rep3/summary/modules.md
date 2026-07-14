# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite persistence, all route handlers | `app`, `get_db()`, `init_db()`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book`, `health` |
| test_app.py | pytest integration tests against the Flask test client | `client` fixture, 11 test functions |
| requirements.txt | Runtime + test deps (`flask`, `pytest`) | — |
| README.md | Setup, run, and curl usage docs | — |
