# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` \| `503 {status:unavailable}` | `api.go:health` |
| POST | /books | `201 Book` (+ Location) \| `400` \| `413` | `api.go:createBook` |
| GET | /books | `200 [Book]` (`?author=` filter) | `api.go:listBooks` |
| GET | /books/{id} | `200 Book` \| `400` \| `404` | `api.go:getBook` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `api.go:updateBook` |
| DELETE | /books/{id} | `204` \| `400` \| `404` | `api.go:deleteBook` |

Unmatched methods on `/health`, `/books`, `/books/{id}` return `405` with an `Allow` header. All errors are JSON `{"error":...,"details":...}`.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER default 0), isbn (TEXT default ''). Case-insensitive index on author.

## Library API

- `store.Open(path) (*Store, error)` — opens/creates SQLite DB (supports `:memory:`).
- `book.Input.Clean() (Input, error)` — trims and validates; returns `ValidationError`.
- `api.New(store, logger) http.Handler` — builds the routed, middleware-wrapped handler.
