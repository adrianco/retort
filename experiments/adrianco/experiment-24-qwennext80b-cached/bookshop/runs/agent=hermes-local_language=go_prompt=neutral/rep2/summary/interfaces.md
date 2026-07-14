# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `main.go:healthHandler` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `main.go:listBooks` |
| POST | /books | `201 Book` \| `400` | `main.go:createBook` |
| GET | /books/{id} | `200 Book` \| `404` \| `400` | `main.go:getBook` |
| PUT | /books/{id} | `200 Book` \| `404` \| `400` | `main.go:updateBook` |
| DELETE | /books/{id} | `204` \| `404` \| `400` | `main.go:deleteBook` |

Routing is done with stdlib `net/http` via `/books` (collection) and `/books/` (item) prefix handlers; the item handler parses the trailing path segment with `strconv.Atoi`.

## Data schema

`books` table (SQLite, `./books.db`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).
