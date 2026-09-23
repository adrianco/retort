# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | WSGI HTTP app, request dispatch, SQLite persistence, validation | `create_app()`, `main()`, `_validated_book()`, `_database()`, `_connect()` |
| test_app.py | unittest integration tests driving the WSGI app in-process | `BookApiTests` (3 test methods) |
