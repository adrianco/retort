# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Stdlib HTTP server, SQLite store, validation, route handlers | `BookStore`, `validate_book()`, `make_handler()`, `create_server()`, `main()` |
| tests/test_app.py | Integration tests against a real server + validation unit tests | 11 test functions (one parametrized ×4) |
