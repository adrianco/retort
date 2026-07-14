# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status: "ok"}` (200) | `app.go:healthCheck` |
| POST | /books | `Book` (201) / error (400, 500) | `app.go:createBook` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `app.go:listBooks` |
| GET | /books/:id | `Book` (200) / 400 / 404 / 500 | `app.go:getBook` |
| PUT | /books/:id | `{message}` (200) / 400 / 404 / 500 | `app.go:updateBook` |
| DELETE | /books/:id | `{message}` (200) / 400 / 404 / 500 | `app.go:deleteBook` |

## Data schema

`books` table:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `title` TEXT NOT NULL
- `author` TEXT NOT NULL
- `year` INTEGER NOT NULL
- `isbn` TEXT NOT NULL UNIQUE

## JSON payloads

- `Book` / `CreateBookRequest` / `UpdateBookRequest`: `{id, title, author, year, isbn}` (id present only on responses).
- Validation: `title` and `author` must be non-empty (checked in `validateBook`); both return `400` with an `{error}` body. `isbn` UNIQUE constraint violation surfaces as `500 {"error": "failed to create book"}`.

## Library API / CLI

(none) — single `main` package binary; server listens on `:8080`, DB file `./books.db`.
