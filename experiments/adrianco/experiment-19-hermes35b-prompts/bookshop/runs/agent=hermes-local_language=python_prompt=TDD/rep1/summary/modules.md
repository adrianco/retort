# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite storage, all route handlers | `create_app()`, `get_db()`, `init_db()` |
| tests/conftest.py | Shared pytest fixture — per-test SQLite DB isolation | `app` fixture |
| tests/test_health.py | Health-check endpoint tests | 3 test functions (`TestHealthCheck`) |
| tests/test_books.py | CRUD, validation, filtering, edge-case tests | 17 test functions (`TestListBooks`) |
| requirements.txt | Dependencies: flask>=3.0, pytest>=7.0 | — |
| README.md | Setup, run, and API reference documentation | — |
