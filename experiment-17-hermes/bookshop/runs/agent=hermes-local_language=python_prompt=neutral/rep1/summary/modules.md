# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask HTTP server, SQLite init, route handlers | `app`, `init_db()`, `get_db_connection()` |
| app_modified.py | Near-identical duplicate of app.py (only listen port differs: 5001 vs 5000) | `app`, `init_db()`, `get_db_connection()` |
| test_app.py | unittest integration tests against `app` | 11 test methods (`BookAPITestCase`) |
| test_app_fixed.py | Duplicate test suite with temp-DB monkeypatching in `setUp` | 11 test methods (`BookAPITestCase`) |
| README.md | Setup, endpoints, curl usage | — |
| requirements.txt | Python deps (`Flask==2.3.3`) | — |
| books.db | SQLite database file (committed build artifact) | — |

Note: the workspace contains two copies of the application (`app.py`, `app_modified.py`)
and two copies of the test suite (`test_app.py`, `test_app_fixed.py`). The agent's own
summary names `app_modified.py` as "the main file", but `README.md` and the tests both
target `app.py`. See `../findings.jsonl`.
