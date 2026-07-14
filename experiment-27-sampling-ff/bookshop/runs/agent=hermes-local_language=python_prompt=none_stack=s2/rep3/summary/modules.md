# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite storage, all route handlers | `app`, `create_app()`, `init_db()` |
| test_app.py | pytest acceptance/integration tests | `client` fixture, `sample_books` fixture, 24 test functions |
| requirements.txt | Python dependencies | flask>=2.0, pytest>=7.0 |
| README.md | Setup, run, and API usage docs | — |
