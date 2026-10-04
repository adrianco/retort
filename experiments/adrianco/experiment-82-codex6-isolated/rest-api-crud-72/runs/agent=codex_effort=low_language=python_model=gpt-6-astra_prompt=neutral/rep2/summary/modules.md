# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask REST API for a persistent book collection | `create_app(database_path=None)`, `__main__` runs dev server on `PORT` (default 5000) |
| test_app.py | API integration tests via Flask test client against temp SQLite files | `BookAPITest` (8 test methods) |
