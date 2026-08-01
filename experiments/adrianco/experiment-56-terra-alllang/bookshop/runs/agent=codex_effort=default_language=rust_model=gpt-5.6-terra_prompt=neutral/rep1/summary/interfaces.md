# Interfaces

## HTTP routes

| Method | Path | Description | Success | Errors |
|--------|------|-------------|---------|--------|
| GET | `/health` | Liveness check | 200 `ok` (text) | — |
| POST | `/books` | Create a book | 201 + Book JSON | 400 (missing title/author) |
| GET | `/books` | List all books; `?author=` exact filter | 200 + `[Book]` | — |
| GET | `/books/{id}` | Fetch one book | 200 + Book | 404 |
| PUT | `/books/{id}` | Replace a book | 200 + Book | 400, 404 |
| DELETE | `/books/{id}` | Delete a book | 204 | 404 |

## Data schema

`books` table: `id INTEGER PK AUTOINCREMENT`, `title TEXT NOT NULL`, `author TEXT NOT NULL`, `year INTEGER NULL`, `isbn TEXT NULL`.

`Book` / `BookInput` JSON: `{ id, title, author, year?, isbn? }` (input omits `id`).
