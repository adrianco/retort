# Architecture Summary

Single-module Flask REST service for a book collection, backed by SQLite.

## Modules

- **`app.py`** (242 LOC) — the entire service.
  - `get_db()` / `close_db()` — per-request SQLite connection via Flask `g`, with
    `row_factory = sqlite3.Row` for dict-like row access.
  - `init_db()` — creates the `books` table (id, title, author, year, isbn,
    created_at, updated_at) if absent. Called under `__main__`.
  - `validate_book_data(data, require_title, require_author)` — shared validator;
    enforces required title/author and a 0–9999 integer year.
  - Routes: `GET /health`, `POST /books`, `GET /books` (with `?author=`),
    `GET /books/<int:id>`, `PUT /books/<int:id>`, `DELETE /books/<int:id>`.
- **`test_app.py`** (264 LOC) — 15 pytest integration tests using `app.test_client()`.
  A fixture swaps the module-level `DATABASE` to `test_books.db` and recreates the
  schema per test.

## Interfaces / flow

Request → route handler → `get_db()` (lazy connection on `g`) → parameterised
SQL (no string interpolation) → serialise row to a fixed dict → `jsonify` +
status code. Teardown closes the connection. Timestamps use `datetime.utcnow()`.

## Notes

- Status codes: 201 create, 200 read/update/delete, 400 validation/empty-body,
  404 not-found. Consistent with the spec.
- PUT is a full replacement (title+author required); the spec does not specify
  partial-update semantics, so this conforms.
