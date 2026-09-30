# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `handlers.go:api.health` |
| POST | /books | `Book` 201 (+ Location) / 400 | `handlers.go:api.create` |
| GET | /books | `[Book]` 200 (optional `?author=`) | `handlers.go:api.list` |
| GET | /books/{id} | `Book` 200 / 400 / 404 | `handlers.go:api.get` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `handlers.go:api.update` |
| DELETE | /books/{id} | 204 / 400 / 404 | `handlers.go:api.delete` |

Errors return `{"error": "..."}` with the appropriate 4xx/5xx status.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, default 0), `isbn` (TEXT, default ''). Index `idx_books_author` on `author`.
