# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | HTTP server, route handlers, JSON I/O, validation, SQLite access | `serve()`, `connect_db()`, `BookHandler` |
| test_app.py | unittest integration tests exercising handlers in-process | `BookApiTests` (3 test methods) |
| README.md | setup / run / endpoint documentation | — |
