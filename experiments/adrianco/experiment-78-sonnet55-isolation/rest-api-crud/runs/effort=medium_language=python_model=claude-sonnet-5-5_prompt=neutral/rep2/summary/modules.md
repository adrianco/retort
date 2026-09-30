# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI HTTP server, hand-rolled router, request handling, SQLite persistence, input validation | `create_app()`, `main()`, `Store`, `validate()`, `ValidationError` |
| test_app.py | HTTP integration tests over a live ephemeral server | 6 test functions (`test_health`, `test_create_and_get`, `test_validation`, `test_list_and_filter`, `test_update_delete`, `test_not_found`) |
