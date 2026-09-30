# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI app: routing, handlers, validation, SQLite access | `BookApp`, `create_app()`, `main()`, `validate_book()`, `HTTPError` |
| tests/test_api.py | In-process WSGI integration tests | `Client`, 11 `test_*` functions |
| README.md | Setup, run, endpoint, and example docs | — |
| requirements.txt | Test-only dependency (`pytest`) | — |
