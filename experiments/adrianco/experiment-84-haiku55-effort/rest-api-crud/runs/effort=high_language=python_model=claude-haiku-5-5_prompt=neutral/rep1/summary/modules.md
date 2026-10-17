# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | HTTP layer: route dispatch, request handling, JSON responses on `http.server` | `BookRequestHandler`, `BookServer`, `create_server()`, `main()` |
| db.py | SQLite storage, one locked connection shared across request threads | `Database` (`list_books`, `get_book`, `create_book`, `update_book`, `delete_book`, `ping`) |
| validation.py | Payload validation and field cleaning for book records | `validate_book()`, `ValidationError` |
| test_api.py | End-to-end API tests against a real server on a free port | 18 test functions |
| test_validation.py | Unit tests for the validation rules | 12 test functions |
| README.md | Setup, run, test, and data-model docs | — |
| requirements-dev.txt | Dev dependency (`pytest>=8`) | — |
