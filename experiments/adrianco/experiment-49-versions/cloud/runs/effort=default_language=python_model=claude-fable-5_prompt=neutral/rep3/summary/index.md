# Architecture Summary

`run-summary` skill not available in this session; concise manual summary below.

- **app.py** — single-module Flask app via `create_app(db_path)` factory. SQLite
  persistence with per-request connection stored on `g` and torn down at context
  exit. Helpers: `book_to_dict` (row→JSON), `validate_payload` (shared by POST/PUT,
  `require_all` toggles create vs partial-update semantics).
- **Routes:** `GET /health`, `POST /books`, `GET /books` (+`?author=` case-insensitive
  exact filter), `GET /books/<int:id>`, `PUT /books/<int:id>` (partial), `DELETE
  /books/<int:id>`. JSON errorhandlers for 404/405.
- **test_app.py** — pytest with `tmp_path` DB fixture; 7 tests covering health, create,
  validation, list+filter, get, update, delete.
- **Flow:** request → JSON parse (silent) → validate → SQLite CRUD → JSON + status code.
