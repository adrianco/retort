# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask app, SQLite schema init, all six HTTP route handlers | `app`, `init_db()`, `get_db_connection()`, `health_check()`, `create_book()`, `get_books()`, `get_book()`, `update_book()`, `delete_book()` |
| `test_app.py` | Flask test-client integration tests over every route | `client` fixture, 11 `test_*` functions |
| `requirements.txt` | Runtime dependency pin | `Flask==2.3.3` |
| `README.md` | Setup, run, endpoint and test instructions | — |
