# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `handlers.go:handleHealth` |
| POST | /books | `Book` 201 / 400 / 413 | `handlers.go:handleCreate` |
| GET | /books | `[Book]` 200 (optional `?author=`) | `handlers.go:handleList` |
| GET | /books/{id} | `Book` 200 / 400 / 404 | `handlers.go:handleGet` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 / 413 | `handlers.go:handleUpdate` |
| DELETE | /books/{id} | 204 / 400 / 404 | `handlers.go:handleDelete` |

Routing uses Go 1.22+ `net/http.ServeMux` method+path patterns, so unmatched
methods yield 405 automatically.

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null),
`author` (TEXT not null), `year` (INTEGER default 0), `isbn` (TEXT default '').
Index `idx_books_author` on `author COLLATE NOCASE`.

## Configuration (env vars)

`ADDR` (default `:8080`), `DB_PATH` (default `books.db`; `:memory:` supported).
