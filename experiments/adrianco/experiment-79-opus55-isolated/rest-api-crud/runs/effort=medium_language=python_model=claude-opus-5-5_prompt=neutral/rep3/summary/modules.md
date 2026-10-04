# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI app, routing, validation, SQLite persistence | `create_app()`, `main()`, `BookStore`, `validate_book()`, `ApiError` |
| test_app.py | In-process + real-HTTP integration tests | 27 test functions (49 cases with parametrize), `Client`, `Response` |
| README.md | Setup and run instructions | — |
| requirements-dev.txt | Test-only dependency (`pytest>=8`) | — |
