# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `handlers.go:health` |
| GET | /books | `[Book]` 200 (supports `?author=` exact, case-insensitive) | `handlers.go:listBooks` |
| POST | /books | `Book` 201 (+`Location`) / 400 | `handlers.go:createBook` |
| GET | /books/{id} | `Book` 200 / 400 / 404 | `handlers.go:getBook` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `handlers.go:updateBook` |
| DELETE | /books/{id} | 204 / 400 / 404 | `handlers.go:deleteBook` |

Method mismatches return 405 with an `Allow` header. Unknown paths return 404.

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null),
`author` (TEXT not null), `year` (INTEGER default 0), `isbn` (TEXT default '').
Index `idx_books_author` on `author COLLATE NOCASE`.

## Storage driver

`modernc.org/sqlite` (pure-Go, no cgo). WAL journal mode, busy_timeout 5000ms,
single open connection.
