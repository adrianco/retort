# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask app factory, SQLite access, route handlers, validation | `create_app()`, `app`, `get_db()`, `init_db()`, `validate_book()`, `book_to_dict()` |
| test_app.py | pytest integration tests (test client + tmp_path DB) | 17 test functions (one parametrized ×5 → 21 cases) |
| requirements.txt | Dependencies | Flask, pytest |
| README.md | Setup, run, and API documentation | — |
