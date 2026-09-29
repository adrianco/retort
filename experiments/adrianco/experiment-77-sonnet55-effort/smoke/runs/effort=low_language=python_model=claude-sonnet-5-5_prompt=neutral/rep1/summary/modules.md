# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | HTTP server, SQLite persistence, route handlers, validation | `init_db()`, `validate()`, `make_handler()`, `create_server()` |
| tests/test_app.py | API integration tests over a live server on an ephemeral port | 5 test functions |
| README.md | Setup/run/test instructions | — |
