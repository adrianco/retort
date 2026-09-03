# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask HTTP server, sqlite3 access, all route handlers | `app`, `init_db()`, `get_db_connection()`, `health_check()`, `create_book()`, `get_books()`, `get_book()`, `update_book()`, `delete_book()` |
| `test_app.py` | pytest integration tests against `app.test_client()` | `client` fixture + 9 `test_*` functions |
| `requirements.txt` | Declared dependencies | `Flask==2.3.3`, `Flask-SQLAlchemy==3.0.5` |
| `README.md` | Setup, run, endpoint and curl documentation | — |

Single-module implementation: no `models.py`/`db.py` split — schema, connection helper and
routes all live in `app.py`. `Flask-SQLAlchemy` is declared but never imported; persistence
is raw `sqlite3`.
