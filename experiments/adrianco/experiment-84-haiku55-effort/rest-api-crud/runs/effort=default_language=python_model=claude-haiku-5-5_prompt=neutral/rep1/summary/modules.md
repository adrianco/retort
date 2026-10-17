# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books_api.py | HTTP server, routing, validation, SQLite storage | `create_server()`, `main()`, `BookStore`, `BookRequestHandler`, `validate_book()`, `ValidationError` |
| test_books_api.py | Integration + unit tests against a live ephemeral-port server | 15 test functions |
| README.md | Setup, run, and API documentation | — |

Standard-library only (`http.server` + `sqlite3`); no dependency manifest, `pytest` used for tests.
