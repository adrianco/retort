# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask HTTP server, SQLite persistence, all route handlers | `app`, `init_db()`, `get_db_connection()`, `health_check()`, `create_book()`, `get_books()`, `get_book()`, `update_book()`, `delete_book()` |
| `test_app.py` | pytest API integration tests against Flask's test client | `client` fixture, 14 test functions |
| `requirements.txt` | Runtime dependency pin | `Flask==2.3.3` |
| `README.md` | Setup, run, test and curl-example docs | — |

Single-module design: routes, validation and SQL all live in `app.py`. No models,
no blueprints, no separate persistence layer.
