# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | stdlib `http.server` routing, request/response handling, CLI entry | `BookRequestHandler`, `BookHTTPServer`, `create_server()`, `main()` |
| store.py | SQLite persistence, thread-safe book store | `BookStore` (`create`, `get`, `list_books`, `update`, `delete`, `ping`, `close`) |
| validation.py | Book payload validation rules | `validate_book()`, `ValidationError` |
| test_books_api.py | Unit + integration tests | 29 test methods across `ValidationTests` (8), `BookStoreTests` (5), `BookApiTests` (16) |
| README.md | Setup, run, API, and behaviour documentation | — |
