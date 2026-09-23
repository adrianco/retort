# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite persistence, route handlers | `create_app()`, `app` |
| tests/test_app.py | API integration tests (unittest) | `BooksApiTests` (4 test methods) |
| requirements.txt | Runtime dependency pin | `Flask>=2.3,<4` |
| README.md | Setup, run, and endpoint docs | — |
