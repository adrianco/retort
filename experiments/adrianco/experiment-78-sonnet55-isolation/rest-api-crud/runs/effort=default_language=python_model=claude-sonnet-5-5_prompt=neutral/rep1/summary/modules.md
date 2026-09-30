# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | HTTP server, SQLite store, routing, validation | `BookStore`, `validate()`, `make_handler()`, `create_server()` |
| test_app.py | HTTP integration tests over a live server | 6 test functions (`test_health`, `test_create_and_get`, `test_validation`, `test_list_and_filter`, `test_update`, `test_delete_and_404`) |
| README.md | Setup, run, endpoint, and test docs | — |
