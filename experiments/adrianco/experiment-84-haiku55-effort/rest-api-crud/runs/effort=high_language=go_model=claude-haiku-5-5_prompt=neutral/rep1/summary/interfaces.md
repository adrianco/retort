# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` / `503 {status:unavailable}` | `server.go:health` |
| POST | /books | `201 Book` (+ Location) / `400` | `server.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `server.go:listBooks` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `server.go:getBook` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `server.go:updateBook` |
| DELETE | /books/{id} | `204` / `404` / `400` | `server.go:deleteBook` |

Fallback routes return JSON `405` (method not allowed, with `Allow` header) and JSON `404` for unknown paths.

## Library API

`store.Store`: `Open(path)`, `Create`, `Get`, `List(author)`, `Update`, `Delete`, `Ping`, `Close`.
`book.Validate(*Book)` → `*ValidationError` (per-field details map).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT ''). Case-insensitive index on `author`.
