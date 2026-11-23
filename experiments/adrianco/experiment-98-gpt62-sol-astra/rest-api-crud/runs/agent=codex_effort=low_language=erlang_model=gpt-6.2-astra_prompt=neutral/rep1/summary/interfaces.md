# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `books.erl:route/4` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `books.erl:route/4` |
| POST | /books | `201 Book` + `Location` header | `books.erl:route/4` |
| GET | /books/{id} | `200 Book \| 404` | `books.erl:item/3` |
| PUT | /books/{id} | `200 Book \| 404` (full replace, id preserved) | `books.erl:item/3` |
| DELETE | /books/{id} | `200 {deleted:id} \| 404` | `books.erl:item/3` |

Unknown routes return 404; wrong method on a known path returns 405 with an `Allow` header. Invalid JSON / missing fields return 400; unhandled exceptions return 500.

## Data schema

DETS table `books_db` (type `set`): key = generated 32-hex-char string `id`; value = book map with keys `id`, `title`, `author`, `year`, `isbn`. Persisted to `books.dets` (overridable via `BOOKS_DB`).
