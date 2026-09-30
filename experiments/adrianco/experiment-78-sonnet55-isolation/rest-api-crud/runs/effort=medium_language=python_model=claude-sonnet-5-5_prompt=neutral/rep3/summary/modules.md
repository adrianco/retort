# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | stdlib WSGI HTTP server, route dispatch, SQLite persistence, validation | `create_app()`, `app`, `handle()`, `validate()`, `init_db()`, `row_to_dict()`, `HTTPError` |
| tests/test_api.py | WSGI-level integration tests (in-process client) | `Client`, 5 test functions (`test_health`, `test_crud_lifecycle`, `test_list_and_author_filter`, `test_validation`, `test_missing_and_invalid`) |
| README.md | setup, run, and endpoint documentation | — |
