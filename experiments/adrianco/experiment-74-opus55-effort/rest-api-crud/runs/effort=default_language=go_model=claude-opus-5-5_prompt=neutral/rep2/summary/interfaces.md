# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` / `503` | `handlers.go:server.health` |
| POST | /books | `201 Book` (+ Location) / `400` | `handlers.go:server.createBook` |
| GET | /books | `200 [Book]` (`?author=` exact, case-insensitive) | `handlers.go:server.listBooks` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `handlers.go:server.getBook` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `handlers.go:server.updateBook` |
| DELETE | /books/{id} | `204` / `404` / `400` | `handlers.go:server.deleteBook` |

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null), `author` (TEXT not null), `year` (INTEGER default 0), `isbn` (TEXT default '').

## Library API

`Store` type wraps `*sql.DB` with `Create`, `List(author)`, `Get(id)`, `Update`, `Delete`, `Ping`, `Close`. `Book` struct is the JSON-tagged domain model.
