# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask app factory, SQLite access, all route handlers, payload validation | `create_app()`, `app`, `init_db()`, `get_db()`, `parse_book_payload()` |
| test_app.py | pytest integration tests exercising every endpoint | 17 test functions, `client` fixture |
| requirements.txt | Runtime/test dependencies | `flask>=3.0`, `pytest>=7.0` |
| README.md | Setup, run, API docs, curl examples | — |
