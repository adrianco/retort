# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `server.go:health` |
| POST | /books | `Book` (201) \| 422 \| 400 | `server.go:createBook` |
| GET | /books | `[Book]` (200) | `server.go:listBooks` (supports `?author=`) |
| GET | /books/{id} | `Book` (200) \| 404 \| 400 | `server.go:getBook` |
| PUT | /books/{id} | `Book` (200) \| 422 \| 404 \| 400 | `server.go:updateBook` |
| DELETE | /books/{id} | 204 \| 404 \| 400 | `server.go:deleteBook` |

Unsupported methods on a known path return 405 (Go 1.22+ `ServeMux` method routing).

## Library API (package main, exported)

- `NewHandler(store *Store) http.Handler`
- `OpenStore(path string) (*Store, error)`; `Store.Create/Get/List/Update/Delete`
- `BookFields.Validate() error`, `BookFields.Normalize()`
- `Book`, `BookFields`, `ValidationError`, `ErrNotFound`

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT ''). Case-insensitive index on `author`.
