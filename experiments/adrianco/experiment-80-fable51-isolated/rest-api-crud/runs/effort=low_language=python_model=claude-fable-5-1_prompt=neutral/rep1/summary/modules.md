# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI HTTP server, routing, validation, SQLite CRUD | `BookApp`, `validate_book`, `ApiError`, `main()` |
| test_app.py | Integration tests over a real local HTTP server + temp SQLite DB | `BookApiTest` (10 test functions) |
| README.md | Setup, run, endpoint, and example documentation | — |
