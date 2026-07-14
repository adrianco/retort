# Architecture Summary

REST API for a book collection, Flask + SQLite, split into two layers plus tests.

## Modules

- **`app.py`** (128 LOC) — Flask HTTP layer. Defines routes: `GET /health`,
  `POST /books`, `GET /books` (with `?author=` filter), `GET /books/<id>`,
  `PUT /books/<id>`, `DELETE /books/<id>`. Performs request-level validation
  (title/author required) and maps `models` return values / `ValueError`s to
  JSON responses with status codes (200/201/400/404).
- **`models.py`** (208 LOC) — SQLite data layer. `init_db` creates the `books`
  table (`id, title, author, year, isbn`, isbn UNIQUE). CRUD helpers
  (`create_book`, `list_books`, `get_book_by_id`, `update_book`, `delete_book`)
  wrap a `get_db()` context manager that commits/rolls back/closes. DB path is
  module-global and overridable via `set_db_path` / monkeypatching `get_db_path`.
- **`test_app.py`** (209 LOC, 15 tests) — pytest suite using Flask's test client
  against a per-test temp SQLite DB (autouse `patch_db` fixture). Covers health,
  create (success/optional fields/missing title/missing author), list
  (empty/all/author-filter), get (found/404), update (full/partial/404),
  delete (success/404).

## Flow

HTTP request → `app.py` route → validation → `models.py` CRUD → SQLite → dict →
`jsonify` → JSON response. Persistence is durable (file-backed SQLite).

## Notes

- `app.py:15-17` `get_db_path()` is dead/confused code (a broken `.__self__`
  expression), never called on the request path. Runtime uses `models.get_db_path`.
- No `README.md` deliverable present.
