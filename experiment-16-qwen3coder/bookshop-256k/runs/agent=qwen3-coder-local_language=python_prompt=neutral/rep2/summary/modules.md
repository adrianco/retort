# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLAlchemy model, all route handlers | `app`, `db`, `Book`, `create_book`, `get_books`, `get_book`, `update_book`, `delete_book`, `health_check` |
| demo.py | Standalone script exercising the API end-to-end | `main()` / `__main__` |
| test_app.py | unittest integration tests for the API | `BookAPITestCase` (11 test methods) |
| requirements.txt | Python dependencies | Flask 2.3.3, Flask-SQLAlchemy 3.0.5 |
| README.md | Setup, run, and usage documentation | — |
