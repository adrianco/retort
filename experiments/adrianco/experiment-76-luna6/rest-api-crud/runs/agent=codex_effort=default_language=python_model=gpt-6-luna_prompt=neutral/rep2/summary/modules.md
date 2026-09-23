# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI HTTP server, routing, SQLite persistence, JSON responses | `create_app()`, `read_book()`, `respond()`, `not_found()` |
| tests/test_api.py | In-process WSGI integration tests | 3 test functions |
