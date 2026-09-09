# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | "Flask REST API backed by a persistent SQLite book collection." — application factory, SQLite connection lifecycle, schema DDL, validation, and all six route handlers | `create_app()`, `health`, `create_book`, `list_books`, `get_book`, `update_book`, `delete_book` |
| `test_app.py` | unittest integration tests driving the Flask test client against a temp-file SQLite DB | `BooksAPITest` (9 test methods) |
| `requirements.txt` | Single runtime dependency pin | `Flask>=2.3,<4` |
| `README.md` | Setup, run, endpoint table, error-contract and test instructions | — |

No package directory, no `src/`, no `tests/` — the whole project is two flat Python files.
