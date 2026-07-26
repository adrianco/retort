# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite persistence, route handlers, validation | `create_app()`, `SCHEMA` |
| test_app.py | pytest API integration tests (temp-DB fixture) | 15 test functions (one parametrized ×6) |
| README.md | Setup, run, and API documentation | — |
| requirements.txt | Dependencies: `flask>=2.3`, `pytest>=7.0` | — |
