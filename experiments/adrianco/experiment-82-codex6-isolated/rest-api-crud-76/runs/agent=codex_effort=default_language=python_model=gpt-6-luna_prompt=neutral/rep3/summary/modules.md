# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI HTTP server, SQLite persistence, all route handling | `app(environ, start_response)`, `_connect`, `_validate`, `_read_json`, `_response` |
| test_app.py | WSGI-level integration tests via a direct `app` call harness | `test_health_and_create_and_fetch`, `test_list_author_filter_and_update`, `test_validation_not_found_and_delete` |
| README.md | Setup, run, endpoint, and test documentation | n/a |
