# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | HTTP server, SQLite store, route handlers, validation, CLI | `make_server()`, `main()`, `BookStore`, `BookHandler`, `validate_book()` |
| test_app.py | Integration tests against a live server on an ephemeral port | 12 test functions (one parametrized ×8) |
| README.md | Setup, run, and endpoint documentation | — |
