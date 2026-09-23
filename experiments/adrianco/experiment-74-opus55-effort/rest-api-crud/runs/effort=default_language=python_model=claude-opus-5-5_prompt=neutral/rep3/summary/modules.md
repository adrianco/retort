# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | HTTP server, SQLite store, request routing, validation | `BookStore`, `validate_book()`, `BookHandler`, `make_server()`, `main()` |
| test_app.py | Integration + unit tests against a real ephemeral server | 11 test functions (one parametrized ×5) |
