# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `handlers.go:health` |
| GET | /books | `[Book]` 200 (`?author=` filter) | `handlers.go:listBooks` |
| POST | /books | `Book` 201 (+`Location`) / 400 | `handlers.go:createBook` |
| GET | /books/{id} | `Book` 200 / 400 / 404 | `handlers.go:getBook` |
| PUT | /books/{id} | `Book` 200 / 400 / 404 | `handlers.go:updateBook` |
| DELETE | /books/{id} | 204 / 400 / 404 | `handlers.go:deleteBook` |

Unmatched methods return 405 with an `Allow` header; unknown paths return 404 as JSON.

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null), `author` (TEXT not null), `year` (INTEGER nullable), `isbn` (TEXT nullable). Index `idx_books_author` on `author COLLATE NOCASE`.

## Exported library API

Package `main` only; no exported library surface beyond the command. Internal types: `Store`, `Book`, `BookInput`, `api`.
