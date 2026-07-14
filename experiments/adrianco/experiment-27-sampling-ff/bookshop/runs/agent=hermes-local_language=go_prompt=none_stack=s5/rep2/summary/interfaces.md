# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status, message}` | `app.go:healthCheck` |
| POST | /books | `201 Book \| 400` | `app.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.go:listBooks` |
| GET | /books/:id | `200 Book \| 404 \| 400` | `app.go:getBook` |
| PUT | /books/:id | `200 Book \| 404 \| 400` | `app.go:updateBook` |
| DELETE | /books/:id | `200 {message} \| 404 \| 400` | `app.go:deleteBook` |

## Data schema

`books` table (SQLite, file `books.db`): id (INTEGER, pk, autoincrement), title (TEXT, not null), author (TEXT, not null), year (INTEGER), isbn (TEXT).

## Request bodies

- `CreateBookRequest`: title (required), author (required), year, isbn.
- `UpdateBookRequest`: title, author, year, isbn — all optional; blank/zero fields fall back to the existing value (partial-update semantics).
