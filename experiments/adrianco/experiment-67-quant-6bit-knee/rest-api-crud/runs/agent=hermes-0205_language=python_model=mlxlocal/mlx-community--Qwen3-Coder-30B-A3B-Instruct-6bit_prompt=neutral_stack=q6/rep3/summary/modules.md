# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask application: SQLite schema init, connection helper, and all six HTTP route handlers | `app`, `init_db()`, `get_db_connection()`, `health_check()`, `create_book()`, `get_books()`, `get_book()`, `update_book()`, `delete_book()` |
| `test_app.py` | pytest integration tests driving the Flask test client | `client` fixture + 10 `test_*` functions |
| `requirements.txt` | Runtime dependency list | `flask` |
| `README.md` | Setup, run, test and curl usage instructions | — |

Generated/ignored: `.coverage`, `__pycache__/`, harness files (`_hermes_session.jsonl`, `_agent_*.log`, `_judge/`, `*.json` metadata).
