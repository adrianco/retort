# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Stdlib WSGI book API + SQLite persistence, routing, validation, threaded server | `BookApp`, `create_app()`, `main()`, `validate_book()`, `init_db()` |
| test_app.py | In-process WSGI integration tests | 8 test functions (one parametrized ×7) |
| README.md | Setup / run / test / endpoint docs | — |
| requirements.txt | Test-only dependency (`pytest`) | — |
