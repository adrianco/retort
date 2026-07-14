# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status:"ok"}` | `app.go:healthCheck` |
| POST | /books | `Book` (201) \| 400 \| 500 | `app.go:createBook` |
| GET | /books | `[Book]` (200, `?author=` filter) | `app.go:listBooks` |
| GET | /books/:id | `Book` (200) \| 400 \| 404 | `app.go:getBook` |
| PUT | /books/:id | `Book` (200) \| 400 \| 404 | `app.go:updateBook` |
| DELETE | /books/:id | `{message}` (200) \| 400 \| 404 | `app.go:deleteBook` |

## Data schema

`books` table: id (INTEGER, pk, autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT). Persisted to `./books.db` via `github.com/mattn/go-sqlite3`.
