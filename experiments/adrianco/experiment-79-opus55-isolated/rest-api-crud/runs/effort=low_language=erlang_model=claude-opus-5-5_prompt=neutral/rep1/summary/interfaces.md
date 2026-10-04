# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: ok}` | `books_health_handler:init/2` |
| POST | /books | `201 Book` + Location, `400` on invalid | `books_handler` (collection) |
| GET | /books | `200 [Book]`, `?author=` filter | `books_handler` (collection) |
| GET | /books/{id} | `200 Book \| 404` | `books_handler` (item) |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `books_handler` (item) |
| DELETE | /books/{id} | `204 \| 404` | `books_handler` (item) |

Unsupported methods on a route return `405` with an `Allow` header. Oversize bodies return `413`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

JSON book shape: `{id, title, author, year, isbn}` — `year`/`isbn` serialize as `null` when absent.
