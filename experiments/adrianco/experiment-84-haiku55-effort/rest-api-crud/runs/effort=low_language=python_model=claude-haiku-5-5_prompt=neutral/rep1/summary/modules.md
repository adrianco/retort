# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | HTTP layer: stdlib routing + JSON responses | `BookRequestHandler`, `make_server()`, `main()` |
| book_store.py | SQLite-backed storage + input validation | `BookStore`, `validate_book()`, `ValidationError` |
| tests/test_api.py | HTTP integration + unit tests | 11 test functions |
