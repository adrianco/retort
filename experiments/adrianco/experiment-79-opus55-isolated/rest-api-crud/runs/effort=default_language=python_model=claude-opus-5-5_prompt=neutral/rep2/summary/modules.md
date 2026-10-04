# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI application: routing, request/JSON parsing, validation, server entry point | `BookAPI`, `validate_book()`, `main()`, `ThreadingWSGIServer` |
| db.py | SQLite persistence layer, connection-per-operation | `BookStore`, `DuplicateISBN` |
| test_app.py | Direct-WSGI and over-HTTP integration tests | 22 test functions (several parametrized) |
