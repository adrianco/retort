# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:_dispatch` |
| POST | /books | `201 Book` (+ `Location` header) \| `400` | `app.py:BookAPI._create` |
| GET | /books | `200 [Book]` (`?author=` case-insensitive exact filter) | `app.py:BookAPI._list` |
| GET | /books/{id} | `200 Book` \| `404` | `app.py:BookAPI._get` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `app.py:BookAPI._update` |
| DELETE | /books/{id} | `204` \| `404` | `app.py:BookAPI._delete` |

Unknown methods on a known path return `405` with an `Allow` header; oversized bodies return `413`.

## Library API

- `create_app(db_path=None) -> BookAPI` — returns a WSGI application callable.
- `BookAPI(db_path)` — WSGI app; `:memory:` uses a shared connection, otherwise a fresh connection per request.
- `validate_book(payload) -> dict` — raises `HTTPError(400)` aggregating all field errors.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
