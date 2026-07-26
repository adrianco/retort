# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask app factory, SQLite schema, route handlers, validation | `create_app()`, `SCHEMA` |
| test_app.py | Integration tests via Flask test client + tmp SQLite DB | 7 test functions |
| requirements.txt | Runtime + test dependencies | `flask>=2.3`, `pytest>=7.0` |
| README.md | Setup, run, API, and test docs | — |
