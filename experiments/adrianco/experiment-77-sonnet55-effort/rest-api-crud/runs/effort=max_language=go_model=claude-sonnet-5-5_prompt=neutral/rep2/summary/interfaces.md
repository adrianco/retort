# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201 Book` + `Location` header / `400` | `handlers.go:createBook` |
| GET | /books | `200 [Book]` (supports `?author=` filter) | `handlers.go:listBooks` |
| GET | /books/{id} | `200 Book` / `400` (bad id) / `404` | `handlers.go:getBook` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204` / `400` / `404` | `handlers.go:deleteBook` |
| GET | /health | `200 {"status":"ok"}` / `503 {"status":"unavailable"}` | `handlers.go:health` |
| (other) | /books, /books/{id}, /health | `405` with `Allow` header | `api.go:methodNotAllowed` |
| (other) | /* | `404 {"error":...}` | `api.go:New` catch-all |

All responses are JSON with `Content-Type: application/json` and `X-Content-Type-Options: nosniff`. Validation failures return `400 {"error":"validation failed","details":{field:reason}}`.

## Data schema

`books` table (SQLite):
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `title` TEXT NOT NULL, CHECK length(trim) > 0
- `author` TEXT NOT NULL, CHECK length(trim) > 0
- `year` INTEGER NOT NULL DEFAULT 0
- `isbn` TEXT NOT NULL DEFAULT ''
- Index `idx_books_author` on `author COLLATE NOCASE` (backs the author filter)

## Library API (internal packages)

- `book.Input.Validate() error` — title/author required, max lengths, year range 0–9999
- `book.Input.Normalize()` — trims whitespace on text fields
- `store.Store` — `Open`, `Create`, `Get`, `List(author)`, `Update`, `Delete`, `Ping`, `Close`
- `api.New(BookStore, *slog.Logger) http.Handler`

## CLI

Flags: `-addr` (env `PORT`, default `:8080`), `-db` (env `DB_PATH`, default `books.db`).
