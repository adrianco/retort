# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask app factory, SQLite plumbing, and all book/health route handlers | `create_app()`, `app`, `get_db()`, `_register_routes()` |
| test_app.py | pytest integration tests exercising every route via `test_client()` | 21 `test_*` functions, `client` fixture |
| requirements.txt | Runtime/test dependencies | `flask>=3.0`, `pytest>=7.0` |
| README.md | Setup, run, and endpoint documentation | — |
