# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` / `503` | `server.go:health` |
| GET | /books | `200 [Book]` (supports `?author=`) | `server.go:listBooks` |
| POST | /books | `201 Book` (+ `Location` header) / `400` | `server.go:createBook` |
| GET | /books/{id} | `200 Book` / `404` | `server.go:getBook` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `server.go:updateBook` |
| DELETE | /books/{id} | `204` / `404` | `server.go:deleteBook` |

Unknown paths return `404` JSON; known paths with wrong methods return `405` with an `Allow` header. Both fallbacks keep every response JSON.

## Data schema

`books` table (SQLite, STRICT): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL, non-empty), `author` (TEXT NOT NULL, non-empty), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API (package main)

- `OpenStore(ctx, path)` — open/create SQLite DB (supports `:memory:`); `Store` CRUD methods.
- `NewServer(store, logger)` — build the `http.Handler`.
- `BookInput.Validate(currentYear)` — returns a `ValidationError` listing every field problem.
