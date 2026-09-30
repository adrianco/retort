# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI HTTP server, routing, validation, SQLite persistence | `create_app()`, `connect()`, `validate()`, module `__main__` server |
| test_app.py | WSGI-level integration tests via an in-process client | `Client`, 7 `test_*` functions |
