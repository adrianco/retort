# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite persistence, route handlers | `app`, `init_db()`, `get_db_connection()`, `validate_book_data()` |
| test_app.py | unittest-based API integration tests | `BookAPITestCase` (11 test methods) |
| README.md | Setup and run instructions, curl usage examples | (docs) |
