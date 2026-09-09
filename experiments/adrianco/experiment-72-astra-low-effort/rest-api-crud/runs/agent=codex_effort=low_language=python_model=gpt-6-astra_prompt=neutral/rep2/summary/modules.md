# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Dependency-free WSGI JSON API for a book collection: schema bootstrap, request dispatch, validation, SQLite persistence | `BookAPI`, `BookAPI.dispatch`, `BookAPI.read_book`, `create_app()`, `__main__` server |
| test_app.py | pytest integration tests driving the WSGI app directly | 5 test functions (`test_crud`, `test_validation`, `test_filter_and_sql_safety`, `test_errors_and_health`, `test_persistence_and_failed_update`) |
