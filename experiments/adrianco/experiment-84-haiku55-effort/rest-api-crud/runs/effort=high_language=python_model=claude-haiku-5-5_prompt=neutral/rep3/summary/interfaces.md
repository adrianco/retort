# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` / `503 {status:unavailable}` | `app.py:BookApp._health` |
| GET | /books | `200 [Book]` (optional `?author=` exact, case-insensitive) | `app.py:BookApp._list_books` |
| POST | /books | `201 Book` + `Location` header | `app.py:BookApp._create_book` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:BookApp._get_book` |
| PUT | /books/{id} | `200 Book` \| `404` | `app.py:BookApp._update_book` |
| DELETE | /books/{id} | `204` \| `404` | `app.py:BookApp._delete_book` |

Error codes: `400` (bad JSON, non-object body, validation failure, non-integer id, empty author filter), `404` (unknown id/route), `405` (method not allowed, with `Allow` header), `413` (body > 1 MB), `415` (non-JSON Content-Type), `500` (unhandled).

## CLI commands

`python -m bookapi [--host H] [--port P] [--db PATH]` — starts the threaded WSGI server. DB path also reads `$BOOKS_DB_PATH`.

## Library API

- `BookApp(store)` — WSGI callable.
- `BookStore(path=":memory:")` — `create_book`, `get_book`, `list_books(author=None)`, `update_book`, `delete_book`, `ping`, `close`.
- `validate_book(payload)` / `is_valid_isbn(isbn)` / `ValidationError`.

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
