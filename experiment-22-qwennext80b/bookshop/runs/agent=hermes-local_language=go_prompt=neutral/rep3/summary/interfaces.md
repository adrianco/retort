# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `server.go:handleHealth` |
| GET | /books | `200 {books,total}` (optional `?author=` filter) | `server.go:listBooks` |
| POST | /books | `201 Book` / `400` / `409` | `server.go:createBook` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `server.go:getBook` |
| PUT | /books/{id} | `200 Book` / `400` / `404` / `409` | `server.go:updateBook` |
| DELETE | /books/{id} | `204` / `404` | `server.go:deleteBook` |

Unsupported methods on `/books` and `/books/{id}` return `405`.

## Data schema

`books` table (GORM auto-migrated): id (uint, pk), title (str, not null), author (str, not null), year (int, not null), isbn (str, unique, not null), created_at, updated_at.
