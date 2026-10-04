# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status: ok}` \| 503 | `app.py:BookAPI.health` |
| GET | /books | `[Book]` (optional `?author=` exact filter) | `app.py:BookAPI.list_books` |
| POST | /books | `Book` (201, `Location` header) \| 400 \| 413 | `app.py:BookAPI.create_book` |
| GET | /books/{id} | `Book` \| 404 | `app.py:BookAPI.get_book` |
| PUT | /books/{id} | `Book` (full replace) \| 400 \| 404 | `app.py:BookAPI.update_book` |
| DELETE | /books/{id} | 204 (no body) \| 404 | `app.py:BookAPI.delete_book` |

Routing notes: trailing slashes are stripped; `HEAD` is answered as `GET` with the body dropped; unmatched methods return 405 with an `Allow` header; `{id}` must be non-negative digits within SQLite's rowid range (else 404).

## CLI commands

`python -m bookapi` (`__main__.py:main`)

| Flag | Default (env override) | Purpose |
|------|------------------------|---------|
| --host | 127.0.0.1 (`BOOKAPI_HOST`) | bind address |
| --port | 8000 (`BOOKAPI_PORT`) | listen port |
| --db | books.db (`BOOKAPI_DB`) | SQLite file path |

## Library API

- `create_app(db_path=":memory:")` — build a `BookAPI` WSGI callable with its own `BookStore`.
- `BookAPI(store)` — WSGI application object.
- `BookStore(path=":memory:")` — `create`, `list(author=None)`, `get`, `update`, `delete`, `ping`, `close`.
- `validate_book(payload)` / `ValidationError` — payload validation.
- `make_threaded_server(host, port, app)` — threaded `wsgiref` server.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Index `idx_books_author` on `author`.

Validation: `title` and `author` required non-empty strings (trimmed, UTF-8-storable); `year` optional int in [-9999, 9999] (rejects bool/float); `isbn` optional string; unknown fields (including `id`) ignored.
