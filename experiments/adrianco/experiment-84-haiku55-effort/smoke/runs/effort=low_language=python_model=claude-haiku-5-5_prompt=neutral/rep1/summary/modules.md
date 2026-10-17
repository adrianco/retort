# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| books_api.py | HTTP server, routing, validation, SQLite storage | `validate_book()`, `BookStore`, `BookRequestHandler`, `create_server()`, `main()` |
| test_books_api.py | Unit + integration tests (stdlib urllib client against a live server) | 11 test functions |
| README.md | Setup, run, and API documentation | — |
| requirements.txt | Test dependency (`pytest>=7`) | — |
