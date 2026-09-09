# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask application factory: SQLite connection management, schema bootstrap, JSON error handler, payload validation, and all book routes | `create_app()`, `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| `test_app.py` | unittest integration tests driving the app through Flask's HTTP test client | `BooksAPITest` (10 test methods) |
| `pyproject.toml` | setuptools packaging metadata; declares `app` as a py-module and a `test` extra | — |
| `requirements.txt` | Runtime dependency pin (`Flask>=2.3.3,<4`) | — |
| `README.md` | Setup/run instructions, route table, request/response contract, test commands | — |
| `.gitignore` | Excludes venvs, `__pycache__`, `*.sqlite3`, build output | — |
