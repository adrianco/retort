# Architecture summary

Single-module Flask app (`app.py`, 109 LOC) using the application-factory pattern.

## Modules / interfaces
- `create_app(db_path=None)` — factory; wires config, per-request SQLite connection
  (`get_db` on `flask.g` with `teardown_appcontext` cleanup), creates the `books`
  table on startup, and registers all routes as closures.
- Helpers: `error(msg, code)` (uniform JSON error envelope), `validate(data)`
  (type + required-field checks, returns `(clean, err)`), `fetch(book_id)`
  (single-row lookup → dict or None).
- Routes: `GET /health`, `POST /books`, `GET /books` (with `?author=`),
  `GET /books/<int:id>`, `PUT /books/<int:id>`, `DELETE /books/<int:id>`.

## Flow
Request → route closure → `validate`/`fetch` → parametrized SQLite query via
`get_db()` → `jsonify` response with explicit status code (201/200/204/400/404).

## Persistence
SQLite via stdlib `sqlite3`; table auto-created; DB path configurable via
`db_path` arg or `BOOKS_DB` env. Tests inject a `tmp_path` DB through the factory.

## Tests
`test_app.py` (5 tests) drives the app through Flask's `test_client`, covering
health, create+get, validation (4 cases), list+author-filter, and update+delete
+404 paths. No skips.
