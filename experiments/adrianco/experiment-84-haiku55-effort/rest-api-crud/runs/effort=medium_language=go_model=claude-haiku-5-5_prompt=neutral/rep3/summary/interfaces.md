# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `handlers.go:health` |
| POST | /books | `Book 201 \| 400 \| 409` | `handlers.go:createBook` |
| GET | /books | `[Book] 200` (optional `?author=`) | `handlers.go:listBooks` |
| GET | /books/{id} | `Book 200 \| 400 \| 404` | `handlers.go:getBook` |
| PUT | /books/{id} | `Book 200 \| 400 \| 404 \| 409` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204 \| 400 \| 404` | `handlers.go:deleteBook` |

Unmatched methods on known paths return `405` with an `Allow` header; unknown paths return `404`. All error bodies are JSON.

## Library API (package `main`)

- `NewServer(store *Store) http.Handler`
- `OpenStore(path string) (*Store, error)` — `":memory:"` supported
- `Store.Create/Get/List/Update/Delete`
- `BookInput.normalize()`, `BookInput.validate(now)`, `isValidISBN`

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null), `author` (TEXT not null), `year` (INTEGER default 0), `isbn` (TEXT unique, nullable).
