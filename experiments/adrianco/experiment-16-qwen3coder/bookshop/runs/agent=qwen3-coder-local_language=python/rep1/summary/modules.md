# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.py | Flask app, SQLAlchemy `Book` model, all route handlers | `app`, `db`, `Book`, `health_check`, `create_book`, `get_books`, `get_book`, `update_book`, `delete_book` |
| tests.py | unittest suite for the API (in-process test client) | `BookAPITestCase` (12 test methods) |
| test_api.py | Manual live-server smoke script (hits `http://localhost:5001`) | `test_health`, `test_books_operations` |
| requirements.txt | Python deps | `Flask==2.3.3`, `Flask-SQLAlchemy==3.0.5` |
| README.md | Setup / run / usage docs | — |

Note: `tests.py` does not match pytest's default discovery pattern (`test_*.py` / `*_test.py`), so it is not collected by the grading harness.
