# Architecture Summary

Single-module Flask REST API backed by SQLite. No package structure; everything
lives in `app.py`.

## Modules

| File | Role |
|------|------|
| `app.py` | Flask app: DB init/connection helpers + 6 route handlers |
| `tests.py` | `unittest` suite (12 tests) using Flask's `test_client()` |
| `simple_test.py` | Live-server smoke test (spawns `app.py`, hits it via `requests`) |
| `books.db` | SQLite datastore (single `books` table) |
| `README.md` | Setup/run/usage docs |

## Interfaces (routes)

- `GET /health` → `{status: healthy}` (200)
- `POST /books` → create; 201 on success, 400 on missing title/author or dup ISBN
- `GET /books` (+ `?author=` LIKE filter) → 200 list
- `GET /books/<int:id>` → 200 or 404
- `PUT /books/<int:id>` → 200, 400 (validation), or 404
- `DELETE /books/<int:id>` → 200 or 404

## Data flow

`init_db()` creates the `books` table (id PK, title/author NOT NULL, year,
isbn UNIQUE) at import time. Each request gets a per-context connection via
`get_db()` stored on Flask's `g`, torn down by `close_db`. Handlers execute
parameterized SQL and return `jsonify`'d rows.

## Notes

- `app.py` lines 1–15 duplicate the imports, `DATABASE` constant, and
  `app = Flask(__name__)` — a botched paste; the second (relative-path)
  `DATABASE` wins. No functional impact but dead/confusing code.
- SQL uses parameterized queries throughout (no injection surface observed).
