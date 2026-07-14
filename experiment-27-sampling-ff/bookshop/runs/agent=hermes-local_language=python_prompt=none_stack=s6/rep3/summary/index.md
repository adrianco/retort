# Architecture Summary — bookshop rest-api-crud (python/flask)

## Overview
Single-module Flask REST API backed by SQLite. All routes, DB helpers, and
schema live in `app.py` (196 lines). Tests in `test_app.py` (13 tests).

## Modules & Interfaces
- **`app.py`**
  - `get_db()` / `close_db()` — per-request SQLite connection stored on Flask `g`,
    WAL journal mode, `Row` factory. Torn down via `@app.teardown_appcontext`.
  - `init_db()` — creates `books(id PK AUTOINCREMENT, title NOT NULL, author NOT NULL, year, isbn)`.
  - `row_to_dict()` — `sqlite3.Row` → dict for JSON serialization.
  - Routes:
    - `GET  /health` → `{"status":"ok"}` 200
    - `POST /books` → validate title/author, insert, 201 (400 on missing/blank)
    - `GET  /books` → list all, optional `?author=` exact-match filter, 200
    - `GET  /books/<int:id>` → 200 / 404
    - `PUT  /books/<int:id>` → partial update (falls back to existing values), 200 / 404 / 400
    - `DELETE /books/<int:id>` → 200 / 404

## Data flow
Request → `get_db()` (lazy connect) → parameterized SQL (no string interpolation,
so injection-safe) → `jsonify` response → connection closed on teardown.

## Test strategy
Pytest with a `client` fixture that swaps `DATABASE` to a temp file and calls
`init_db()` per test. Covers health, create (+ missing title/author), list
(empty/populated/author-filter), get (found/404), update (found/404/partial),
delete (found/404). No skips.

## Notes
- `app.run(debug=True)` in the `__main__` guard — dev-only, not used under test.
- `?author=` filter is exact-match (case-sensitive); spec only asks for a filter.
