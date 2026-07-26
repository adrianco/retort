# Architecture — Book Collection API (Flask + sqlite3)

A small, layered Flask service. No ORM; the standard-library `sqlite3` module
handles persistence. Entry point `app.py` calls `bookapi.create_app()`.

## Modules

| Module | Responsibility |
|--------|----------------|
| `bookapi/__init__.py` | `create_app(database=None)` factory — wires config, DB init, error handlers, blueprint. `BOOKS_DB` env var → `books.db` default. |
| `bookapi/db.py` | SQLite connection lifecycle bound to the Flask app context (`get_db`/`close_db`), schema DDL (`books` table, unique `isbn`, author index), `init_db`. |
| `bookapi/repository.py` | Data access: `list_books` (case-insensitive author LIKE with wildcard escaping), `get_book`, `create_book`, `replace_book`, `delete_book`, `ping`. Maps `IntegrityError` → 409 duplicate-ISBN. |
| `bookapi/validation.py` | `validate_book` collects *all* field errors at once; required title/author, optional year range, ISBN-10/13 check-digit validation + normalisation. |
| `bookapi/routes.py` | Blueprint with `/health`, and CRUD on `/books`. Content-type guarding (415), malformed-JSON (400), 404 helpers. |
| `bookapi/errors.py` | `ApiError` type + handlers rendering every failure (incl. Werkzeug HTTP errors) as JSON. |

## Request flow

`app.py` → `create_app` → blueprint route → `_json_body()` (JSON/content-type
guards) → `validate_book` → `repository.*` → `get_db()` (per-context connection)
→ JSON response via `jsonify`. Errors raised as `ApiError` are caught by the
registered handlers and serialised to JSON with the right status code.

## Persistence

SQLite file DB; schema created idempotently on startup. Connection per app
context, committed per write. Restart-durability is covered by a test that opens
a second app over the same file.

## Tests

`tests/test_books_api.py` drives the API through Flask's test client against a
throwaway `tmp_path` SQLite file (fixtures in `conftest.py`). 26 test functions,
36 effective test items (two parametrized), zero skips.
