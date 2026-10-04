# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI REST API, routing, validation, SQLite storage | `create_app()`, `main()`, `BookStore`, `validate_book()`, `ApiError`, `QuietHandler` |
| test_app.py | In-process + real-HTTP integration tests | 20 test functions (incl. parametrized cases) |
| README.md | Setup, run, and API documentation | (docs) |
| requirements-dev.txt | Test-only dependency (`pytest>=8`) | (manifest) |
