# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.py:_route` |
| POST | /books | `201 Book \| 400` | `app.py:create_book` |
| GET | /books | `200 [Book]` (optional `?author=` exact, case-insensitive) | `app.py:list_books` |
| GET | /books/{id} | `200 Book \| 404` | `app.py:get_book` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `app.py:update_book` |
| DELETE | /books/{id} | `204 \| 404` | `app.py:delete_book` |

Unsupported methods on a known path return `405`; unknown paths return `404`.
Malformed/oversized JSON bodies return `400`.

## Data schema

`books` table: `id` (int, pk, autoincrement), `title` (text, not null),
`author` (text, not null), `year` (int, nullable), `isbn` (text, nullable).
