# Architecture Summary

Single-module Flask REST API backed by SQLite. No blueprints, no service layer —
the whole app is one file.

## Modules

- **`app.py`** (167 lines) — the entire service.
  - `get_db()` / `close_db()` — per-request SQLite connection stored on Flask's `g`,
    torn down via `@app.teardown_appcontext`. `row_factory = sqlite3.Row` so rows
    serialize to dicts.
  - `init_db()` — idempotent `CREATE TABLE IF NOT EXISTS books`. Called at import
    time (`app.py:164`) and by the test fixture.
  - Routes: `GET /health`, `POST /books`, `GET /books` (with `?author=` LIKE filter),
    `GET /books/<int:id>`, `PUT /books/<int:id>`, `DELETE /books/<int:id>`.
- **`test_app.py`** (199 lines) — 12 pytest tests using `app.test_client()` and a
  temp-file DB fixture that swaps `app_module.DATABASE`.

## Data model

`books(id INTEGER PK AUTOINCREMENT, title TEXT NOT NULL, author TEXT NOT NULL,
year INTEGER, isbn TEXT)`.

## Request flow

Request → route handler → `get_db()` (lazily opens connection) → parameterized
SQL (no injection risk) → `jsonify` with explicit status code → connection closed
on context teardown.

## Notes

- Validation is inline in `create_book`/`update_book` (title & author required,
  trimmed). PUT does partial-update semantics via `data.get(field, existing)`.
- Parameterized queries throughout — no SQL string interpolation.
- No pagination, auth, or ISBN/year format validation (none required by the spec).
