# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `Book` (201) + `Location` header; 400/413 on bad input | `api.go:handler.create` |
| GET | /books | `[Book]` (200), optional `?author=` exact case-insensitive filter | `api.go:handler.list` |
| GET | /books/{id} | `Book` (200) \| 400 \| 404 | `api.go:handler.get` |
| PUT | /books/{id} | `Book` (200) \| 400 \| 404 \| 413 | `api.go:handler.update` |
| DELETE | /books/{id} | 204 \| 400 \| 404 | `api.go:handler.delete` |
| GET | /health | `{"status":"ok"}` (200) \| 503 if DB ping fails | `api.go:handler.health` |

Unknown paths return 404 JSON; unsupported methods return 405 JSON with an `Allow` header.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT ''). Index `idx_books_author` on `author COLLATE NOCASE`.

## Library API

- `books.Open(path) (*Store, error)` — opens/creates SQLite DB, applies schema.
- `books.Store` methods: `Create`, `Get`, `List`, `Update`, `Delete`, `Ping`, `Close`.
- `books.Input.Clean()` — trims and validates; returns `ValidationError` map.
- `api.New(store, logger) http.Handler` — wired router with logging + panic-recovery middleware.
