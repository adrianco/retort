# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` · 200/503 | `handlers.go:health` |
| POST | /books | `Book` · 201 (400 on invalid) | `handlers.go:createBook` |
| GET | /books | `[Book]` · 200, `?author=` exact filter | `handlers.go:listBooks` |
| GET | /books/{id} | `Book` · 200 / 404 | `handlers.go:getBook` |
| PUT | /books/{id} | `Book` · 200 / 404 | `handlers.go:updateBook` |
| DELETE | /books/{id} | (empty) · 204 / 404 | `handlers.go:deleteBook` |

Routing uses Go 1.22+ method-aware `http.ServeMux` patterns (e.g. `GET /books/{id}`).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL), `isbn` (TEXT NOT NULL DEFAULT '').

Driver: `modernc.org/sqlite` (pure Go, no cgo). `MaxOpenConns(1)` keeps a single writer and keeps `:memory:` DBs alive across requests.

## Validation

`title` and `author` required (non-blank after trim); `year` in `[0, next year]`; unknown JSON fields rejected (`DisallowUnknownFields`); body capped at 1 MiB.
