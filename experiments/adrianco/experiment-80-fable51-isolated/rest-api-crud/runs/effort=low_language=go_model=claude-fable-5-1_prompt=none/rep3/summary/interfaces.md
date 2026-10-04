# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` \| 503 | `main.go:health` |
| POST | /books | `Book` (201) \| 400 | `main.go:createBook` |
| GET | /books | `[Book]` (200), optional `?author=` | `main.go:listBooks` |
| GET | /books/{id} | `Book` (200) \| 404 \| 400 | `main.go:getBook` |
| PUT | /books/{id} | `Book` (200) \| 404 \| 400 | `main.go:updateBook` |
| DELETE | /books/{id} | 204 \| 404 \| 400 | `main.go:deleteBook` |

Errors are returned as JSON `{"error": "message"}`.

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null), `author` (TEXT not null), `year` (INTEGER default 0), `isbn` (TEXT default '').

## Library API

Exported symbols usable as a package: `Book`, `Server`, `OpenDB(dsn)`, `NewServer(db)`, `Server.Handler()`.
