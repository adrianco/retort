# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books_api.py | HTTP server, routing, validation, SQLite storage | `BookStore`, `validate_book()`, `make_handler()`, `create_server()`, `main()` |
| test_books_api.py | Integration tests driving the real server on an ephemeral port | 12 test functions, `base_url` fixture |
| README.md | Setup, run, and endpoint documentation | — |
