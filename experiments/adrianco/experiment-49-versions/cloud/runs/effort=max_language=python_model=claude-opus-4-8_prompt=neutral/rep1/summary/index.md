# Architecture Summary

A single-module Flask REST API backed by SQLite, with a pytest suite.

## Modules

| File | Role |
|------|------|
| `app.py` | Flask application: DB helpers, validation, `create_app` factory, all routes, JSON error handlers. |
| `test_app.py` | 33 pytest unit + integration tests against a temp SQLite DB per test. |
| `README.md` | Setup, run, API reference, examples. |
| `requirements.txt` / `requirements-dev.txt` | Runtime (`Flask`) and test (`pytest`) deps. |

## Key interfaces (`app.py`)

- **DB layer:** `get_db()` (per-context connection on `flask.g`), `close_db()` (teardown), `init_db()` (creates `books` table), `get_book_row()`, `book_to_dict()`.
- **Validation:** `validate_book_payload(data) -> (clean, errors)` — enforces required `title`/`author`, optional integer `year` (0–9999, rejects bool), optional string `isbn`. `_json_body()` safely parses the request body.
- **Factory:** `create_app(database=None)` — configures the DB path (arg → `BOOKS_DB` env → `books.db`), initializes the schema, registers routes and error handlers.

## Routes

`GET /health`, `POST /books`, `GET /books` (+ `?author=` case-insensitive exact match), `GET /books/<int:id>`, `PUT /books/<int:id>` (full replace), `DELETE /books/<int:id>`. JSON error handlers for 404/405/500.

## Flow

Request → `_json_body()` / `validate_book_payload()` → SQLite via `get_db()` → `book_to_dict()` → `jsonify` with the appropriate status code. Connections are opened lazily per request and closed on app-context teardown.
