# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bookapi.py | Stdlib HTTP server, request routing, SQLite persistence, input validation | `validate_book()`, `BookStore`, `Handler`, `make_server()`, `main()` |
| tests/test_api.py | End-to-end API tests against a live server on an ephemeral port | 10 test functions (one parametrized, 9 cases) |
