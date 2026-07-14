# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `app.go:healthHandler` |
| POST | /books | `Book` (201) / error (400/500) | `app.go:createBookHandler` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `app.go:listBooksHandler` |
| GET | /books/:id | `Book` (200) / 404 | `app.go:getBookHandler` |
| PUT | /books/:id | `Book` (200) / 404 / 400 | `app.go:updateBookHandler` |
| DELETE | /books/:id | `{"message":"book deleted"}` (200) / 404 | `app.go:deleteBookHandler` |

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Request bodies

- `CreateBookRequest`: `title` (required), `author` (required), `year`, `isbn` — validated via Gin `binding:"required"`.
- `UpdateBookRequest`: all fields optional; partial update via zero-value substitution against the existing row.
