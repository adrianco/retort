# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI JSON API + SQLite persistence, all route handling in one `application` closure | `create_app()`, `app`, `_connect()`, `_book()` |
| test_app.py | unittest integration tests driving the WSGI callable directly | `BookApiTests` (3 test methods) |
| README.md | setup and run instructions | (docs) |
