# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:route` |
| POST | /books | `201 Book \| 400 \| 413` | `app.py:route` → `store.create` |
| GET | /books | `200 [Book]` (`?author=` filter) | `app.py:route` → `store.list` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:route` → `store.get` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `app.py:route` → `store.update` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:route` → `store.delete` |

Unknown paths → `404 {"error":"Not found"}`; unsupported methods → `405` with an
`Allow` header; bodies over 1 MB → `413`.

## Library API

- `create_app(db_path=DEFAULT_DB_PATH)` — returns a WSGI application.
- `BookStore(db_path)` — `create/list/get/update/delete` over SQLite.
- `validate_book(data)` — returns a cleaned dict or raises `ApiError(400)`.
- `ApiError(status, message, details, headers)` — maps onto a JSON error response.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
