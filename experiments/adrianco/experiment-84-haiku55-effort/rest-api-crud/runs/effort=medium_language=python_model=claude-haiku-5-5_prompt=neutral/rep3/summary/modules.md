# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite persistence, validation, route handlers | `create_app()`, `validate_book()`, `row_to_dict()`, `ValidationError` |
| test_app.py | pytest suite: endpoints, validation, error handling, persistence | 16 test functions (incl. 1 parametrized × 8 cases) |
| requirements.txt | Pinned dependencies | Flask, pytest, Werkzeug |
| README.md | Setup, run, and API documentation | — |
