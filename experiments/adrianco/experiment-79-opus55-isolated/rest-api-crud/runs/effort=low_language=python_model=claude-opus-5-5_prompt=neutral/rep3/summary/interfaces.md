# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:_route` |
| POST | /books | `201 Book \| 422 \| 400 \| 409` | `app.py:_route` → `BookStore.create` |
| GET | /books | `200 [Book]` (`?author=` filter) | `app.py:_route` → `BookStore.list` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:_route` → `BookStore.get` |
| PUT | /books/{id} | `200 Book \| 404 \| 422 \| 409` | `app.py:_route` → `BookStore.update` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:_route` → `BookStore.delete` |

Unsupported methods on a known path return `405` with an `Allow` header.

## Data schema

`books` table (SQLite): `id` (int, pk autoincrement), `title` (text, not null),
`author` (text, not null), `year` (int, nullable), `isbn` (text, unique nullable).

## Library API

- `make_server(host, port, db_path, quiet)` — builds a `ThreadingHTTPServer` with a bound store.
- `validate_book(data)` — returns a cleaned dict or raises `ValidationError`.
- `BookStore` — `create`, `list`, `get`, `update`, `delete`, `close` (thread-locked).
