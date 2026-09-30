# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Stdlib WSGI app, route dispatch, validation, SQLite persistence | `create_app()`, `connect()`, `validate()`, `ValidationError` |
| test_app.py | WSGI-level integration tests via an in-process `Client` | 6 `test_*` functions, `Client`, `client` fixture |
| README.md | Setup, run, endpoint reference, curl example | — |
