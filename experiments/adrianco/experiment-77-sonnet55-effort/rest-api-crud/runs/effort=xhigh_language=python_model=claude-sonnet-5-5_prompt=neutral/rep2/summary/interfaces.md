# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `app.py:_health` |
| GET | /books | `[Book]` (optional `?author=` exact, case-insensitive filter) | `app.py:_list_books` |
| POST | /books | `Book` (201, `Location` header) \| 400 | `app.py:_create_book` |
| GET | /books/{id} | `Book \| 404` | `app.py:_get_book` |
| PUT | /books/{id} | `Book` \| 400 \| 404 (partial update) | `app.py:_update_book` |
| DELETE | /books/{id} | 204 \| 404 | `app.py:_delete_book` |

Routing notes: trailing slashes are stripped; `{id}` must match `[0-9]+`; unmatched paths → 404; known path with wrong method → 405 with an `Allow` header. Unhandled exceptions → 500. Request bodies over 1 MiB → 413; malformed JSON or bad `Content-Length` → 400.

## CLI

`python -m bookapi` (`__main__.py:main`) with flags:

| Flag | Default (env fallback) |
|------|------------------------|
| `--host` | `127.0.0.1` (`HOST`) |
| `--port` | `8000` (`PORT`) |
| `--db` | `books.db` (`BOOKS_DB`) |

## Library API

- `BookApp(store)` — WSGI callable.
- `BookStore(path="books.db")` — `create`, `list_books`, `get`, `update`, `delete`, `ping`, `close`.
- `validate_book(payload, *, partial=False) -> (clean, errors)`.
- `create_server(host, port, db_path) -> (server, store)`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable). Index `idx_books_author` on `author`.

Validation rules: `title`/`author` required, non-blank strings ≤ 500 chars; `year` optional integer in 0..9999 (booleans rejected); `isbn` optional string ≤ 32 chars. Unknown keys (including `id`) ignored.
