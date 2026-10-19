# Architecture Summary

Single-module Flask REST API (`app.py`, 190 LOC) backed by SQLite, with a
companion `unittest` suite (`test_app.py`, 199 LOC).

## Modules

- **`app.py`** — the whole service.
  - **Persistence**: `sqlite3` connection per request via Flask's `g` and
    `teardown_appcontext` (`get_db`, `close_db`). Table bootstrapped by
    `_ensure_table` (per-request, lazy) and `init_db` (eager, used by tests).
    Schema: `books(id PK AUTOINCREMENT, title NOT NULL, author NOT NULL, year, isbn)`.
  - **Routes**:
    - `GET /health` → `{"status":"ok"}`, 200
    - `POST /books` → validates title/author non-empty, inserts, returns 201
    - `GET /books` → lists all, optional `?author=` exact-match filter, 200
    - `GET /books/<int:id>` → single book or 404
    - `PUT /books/<int:id>` → partial update (falls back to existing values), 200 / 404
    - `DELETE /books/<int:id>` → removes, 200 / 404

## Interfaces / flow

Request → route handler → `get_db()` (lazy connect + table ensure) →
parameterised SQL → `jsonify` with explicit status code. Input validation
(`title`/`author` required, trimmed) guards both `POST` and `PUT`. All queries
use bound parameters (no string interpolation), so no SQL-injection surface.

## Tests

10 `unittest` cases using Flask's `test_client`, each with a fresh temp-file DB
(`setUp`/`tearDown`). Covers health, create (+ missing-title / missing-author),
list, author filter, get (+ not-found), update, delete (+ verify-gone). No skips.
