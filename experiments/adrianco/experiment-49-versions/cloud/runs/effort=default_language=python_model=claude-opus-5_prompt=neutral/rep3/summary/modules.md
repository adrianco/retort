# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask application factory, HTTP routes, error handlers | `create_app()`, `error_response()` |
| db.py | SQLite schema, per-request connection, row → JSON | `get_db()`, `close_db()`, `init_db()`, `row_to_book()` |
| validation.py | Book payload validation rules | `validate_book()`, `normalize_isbn()`, `ValidationError` |
| test_api.py | Integration tests driving the real Flask app | 25 test functions (one parametrized ×9 → 33 cases) |
| conftest.py | Pytest fixtures (`client`, `sample_book`) | `client`, `sample_book` |
