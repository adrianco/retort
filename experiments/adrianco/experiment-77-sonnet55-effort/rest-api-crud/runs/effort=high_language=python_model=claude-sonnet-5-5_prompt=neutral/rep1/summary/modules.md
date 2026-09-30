# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI HTTP server, SQLite persistence, routing, validation | `BookAPI`, `create_app()`, `validate_book()`, `main()` |
| tests/test_api.py | WSGI-level integration tests via an in-process client | 12 `test_*` functions, `Client` |
| requirements.txt | Test-only dependency pin | `pytest` |
| README.md | Setup, run, endpoint and error docs | — |
