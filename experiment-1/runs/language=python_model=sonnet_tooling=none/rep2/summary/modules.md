# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.py | HTTP server with route handlers and database initialization | `app` (FastAPI instance), `init_db()`, `get_db()` |
| test_api.py | API integration tests using TestClient | 12 test functions covering all endpoints |

**Total:** 2 files, 131 lines of production code, 108 lines of test code.

**Dependencies:** FastAPI, Pydantic, sqlite3 (stdlib)
