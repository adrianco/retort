# Architecture Summary: books-api

A REST API for a book collection, built entirely on the Python standard library
(`wsgiref` for HTTP, `sqlite3` for storage). The only external dependency is
`pytest` for the test suite.

## Modules

| Module | Responsibility |
|--------|----------------|
| `books/app.py` | WSGI application. Routing, request parsing, error → HTTP-status mapping, and the threaded dev server (`make_books_server`, `main`). |
| `books/db.py` | `BookStore` — SQLite persistence. One shared connection guarded by a `threading.Lock` (safe for the threaded server and for `:memory:` DBs). CRUD + `ping`. Raises `DuplicateISBNError` on the `isbn` UNIQUE constraint. |
| `books/validation.py` | `parse_book` — validates/normalises a payload; required `title`/`author`, optional `year` (1..next year) and `isbn` (ISBN-10/13 checksum, hyphen/space-normalised). Collects all field errors at once. |
| `books/__main__.py` | `python -m books` entrypoint → `app.main()`. |

## Request flow

`BooksApp.__call__` → `route()` dispatches by path/method:
- `/health` → `_health` (pings the DB; 200 ok / 503 unavailable)
- `/books` GET→`_list` (optional `?author=` case-insensitive filter), POST→`_create` (201 + `Location`)
- `/books/{id}` GET→`_get`, PUT→`_update`, DELETE→`_delete` (204)

Errors are modelled as a `RequestError(status, message, details)` exception caught
in `__call__` and rendered as a JSON `{"error": ...}` body; unexpected exceptions
become a 500. Bodies are size-capped (`MAX_BODY_BYTES`) and oversized IDs are
treated as 404 rather than crashing.

## Interfaces

- HTTP/JSON surface described above, with conventional status codes
  (201/200/204/400/404/405/409/413/500) and `Allow` headers on 405.
- `create_app(db_path=None)` wires a `BookStore` (path from `BOOKS_DB_PATH`) into
  a `BooksApp`, suitable for tests and WSGI servers alike.

## Testing

- `tests/conftest.py` — in-process WSGI `Client` (no socket) plus `store`,
  `client`, and `live_server` fixtures (the last runs a real threaded server).
- `tests/test_api.py` — end-to-end CRUD, filtering, validation, conflict,
  routing/method, persistence-to-file, and a live-server round trip.
- `tests/test_validation.py` — unit tests for `parse_book` (ISBN/year edge cases).
