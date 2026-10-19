# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask app factory, SQLite setup, CRUD + health route handlers | `create_app()`, `main()` |
| test_app.py | pytest integration tests against the app factory | 27 `test_*` functions, `client` fixture, `make_book` helper |
| requirements.txt | Single runtime dependency | `flask>=3.0` |
| README.md | Setup, run, API, and field-rules documentation | — |
