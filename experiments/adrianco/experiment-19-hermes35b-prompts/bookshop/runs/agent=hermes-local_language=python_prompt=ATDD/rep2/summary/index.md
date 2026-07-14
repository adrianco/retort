# Run Summary — Book API (Flask/SQLite)

## Surface

A REST API for managing a book collection (CRUD over `/books`, author filter,
health check), backed by SQLite, built with Flask. Written in the ATDD style:
acceptance tests express the requirements as an external HTTP client.

## Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `app.py` | Flask app, all route handlers, SQLite access, validation, schema init | `app`, `get_db()`, `init_db()`, `validate_book_data()`, route fns |
| `test_app.py` | 25 acceptance tests (HTTP client, 7 classes) | `Test*` classes |
| `conftest.py` | `clean_db` autouse fixture — deletes all books before each test via HTTP | `clean_db` |
| `README.md` | Setup/run/test instructions | — |
| `books.db` | SQLite store (auto-created at import via `init_db()`) | — |

## Interfaces (HTTP)

- `GET /health` → 200 `{"status":"ok"}`
- `POST /books` → 201 book | 400 `{"error"}`
- `GET /books[?author=]` → 200 `[book]`
- `GET /books/<int:id>` → 200 book | 404
- `PUT /books/<int:id>` → 200 book | 400 | 404
- `DELETE /books/<int:id>` → 200 `{"message"}` | 404

## Control flow

Per-request SQLite connection stored on Flask `g` (`get_db`), closed in
`teardown_appcontext`. `init_db()` runs at import time (module level) creating
the `books` table. Validation is centralized in `validate_book_data()` with a
`check_empty` flag distinguishing create (all required) from update (validate
only supplied fields).

## Notable structural issue

The suite is pure black-box HTTP against `http://127.0.0.1:5001`, but nothing
in the run starts that server, and `app.py` actually binds **port 5000**. So the
tests only pass when a human manually launches a server on 5001 — they do not
self-host. Under the scoring harness (`pytest --cov`, no server) every test
errors on connection, leaving `app.py` at ~0% coverage (overall 14%).
