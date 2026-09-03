# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask app, SQLite connection helpers, all six route handlers | `app`, `get_db_connection()`, `init_db()`, `health_check()`, `create_book()`, `get_books()`, `get_book()`, `update_book()`, `delete_book()` |
| `test_app.py` | pytest API integration tests against Flask's test client | `client` fixture + 9 `test_*` functions |
| `requirements.txt` | Single runtime dependency | `Flask==2.3.3` |
| `README.md` | Setup, run, endpoint list, curl examples, test command | — |
| `IMPLEMENTATION_SUMMARY.md` | Agent-authored summary of what it built | — |
