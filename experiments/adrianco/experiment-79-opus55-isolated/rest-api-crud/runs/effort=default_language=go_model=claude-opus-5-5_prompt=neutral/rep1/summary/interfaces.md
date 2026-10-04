# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `handlers.go:health` |
| POST | /books | `Book (201) \| 400` | `handlers.go:createBook` |
| GET | /books | `[Book] (200)` — `?author=` exact filter | `handlers.go:listBooks` |
| GET | /books/{id} | `Book (200) \| 404 \| 400` | `handlers.go:getBook` |
| PUT | /books/{id} | `Book (200) \| 404 \| 400` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204 \| 404 \| 400` | `handlers.go:deleteBook` |

Go 1.22 `net/http` method-and-wildcard routing (`ServeMux`); a `PATCH` on a
declared path yields a 405. Request bodies are capped at 1 MiB and must be a
single JSON object (trailing data rejected).

## Library API (package main)

- `NewHandler(store *Store) http.Handler`
- `NewStore(dsn string) (*Store, error)` — accepts `:memory:`
- `Store.{Create,List,Get,Update,Delete,Ping,Close}`
- `Book{ID, Title, Author, Year, ISBN}`, `ErrNotFound`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').
Case-insensitive index `idx_books_author` on `author`.
