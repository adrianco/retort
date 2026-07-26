# Architecture Summary

Book collection REST API — Flask + SQLite, single-module design.

## Modules

- **`app.py`** (182 LOC) — the entire service, built via an application factory
  `create_app(db_path)`.
  - `_init_db(db_path)` — creates the `books` table (`id, title, author, year, isbn`)
    idempotently at app construction.
  - `_get_db()` — lazily opens a per-request `sqlite3.Connection` cached on `flask.g`,
    with `row_factory = sqlite3.Row`; torn down in `teardown_appcontext`.
  - `_validate_payload(payload, partial)` — shared validation for POST (full) and PUT
    (partial): enforces `title`/`author` non-empty strings, type-checks `year`/`isbn`,
    and rejects unknown fields.
  - `_row_to_book(row)` — serializes a DB row to the JSON book shape.
  - Routes: `GET /health`, `POST /books`, `GET /books` (+`?author=`), `GET /books/<id>`,
    `PUT /books/<id>`, `DELETE /books/<id>`.
- **`test_app.py`** (120 LOC) — 8 pytest integration tests using `app.test_client()` and a
  fresh `tempfile` SQLite DB per test.

## Flow

Client → Flask route → `_get_db()` (per-request SQLite connection) → parameterized SQL →
`_row_to_book` → `jsonify` with explicit status code. Validation runs before any write.

## Notes

- Application-factory pattern keeps the app testable with an injectable `db_path`.
- All SQL uses bound parameters (no injection surface).
- Status codes: 200 / 201 / 204 / 400 / 404 used appropriately.
