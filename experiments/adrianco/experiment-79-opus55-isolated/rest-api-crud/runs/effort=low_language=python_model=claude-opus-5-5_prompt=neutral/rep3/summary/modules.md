# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | HTTP server, routing, SQLite store, validation | `make_server()`, `main()`, `BookStore`, `BookHandler`, `validate_book()` |
| test_app.py | Integration tests against the live server + unit tests for validation | `BookAPITest` (11 tests), `ValidateBookTest` (2 tests) |
| README.md | Setup, run, endpoint, and error documentation | — |
