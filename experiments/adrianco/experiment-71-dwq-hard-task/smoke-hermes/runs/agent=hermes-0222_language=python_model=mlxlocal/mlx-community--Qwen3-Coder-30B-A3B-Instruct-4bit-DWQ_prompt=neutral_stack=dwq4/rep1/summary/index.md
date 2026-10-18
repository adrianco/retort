# Architecture Summary — Book API (Flask + SQLite)

Single-module Flask REST service.

## Modules

- **`app.py`** (187 lines) — the whole application. Defines the Flask `app`, a
  module-level `DATABASE = 'books.db'` path, and all routes.
  - `init_db()` — creates the `books` table (`id` PK autoincrement, `title`/`author`
    `NOT NULL`, `year`, `isbn`) if absent.
  - `get_db_connection()` — opens a connection with `row_factory = sqlite3.Row`.
  - Routes: `GET /health`, `POST /books`, `GET /books` (+`?author=` filter),
    `GET /books/<int:id>`, `PUT /books/<int:id>`, `DELETE /books/<int:id>`.
- **`test_app.py`** (222 lines) — `unittest` suite, 9 tests via `app.test_client()`,
  with per-test DB reset in `setUp`/`tearDown`.
- **Scratch files** — `verify.py`, `verify2.py`, `final_report.py`: the agent's own
  ad-hoc verification scripts, not part of the deliverable spec.

## Interfaces / data flow

HTTP request → Flask route → fresh SQLite connection per request → parameterized SQL
→ `dict(row)` → `jsonify(...)`, with status codes 200/201/400/404/500. Persistence is a
real on-disk SQLite file (`books.db`). No ORM, no blueprints, no app factory.

## Notes

- Validation is presence-only (`'title' in data and 'author' in data`); empty strings pass.
- Author filter is a substring `LIKE '%author%'` match, not exact.
- `app.run(debug=True, host='0.0.0.0')` is left on for local dev.
