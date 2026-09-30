# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `server.go:health` |
| POST | /books | `Book (201)` + `Location` | `server.go:createBook` |
| GET | /books | `[Book]` (optional `?author=`) | `server.go:listBooks` |
| GET | /books/{id} | `Book \| 404` | `server.go:getBook` |
| PUT | /books/{id} | `Book \| 404 \| 422` | `server.go:updateBook` |
| DELETE | /books/{id} | `204 \| 404` | `server.go:deleteBook` |

Uses the Go 1.22+ `net/http` method-and-pattern router (`GET /books/{id}`), no third-party web framework.

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null), `author` (TEXT not null), `year` (INTEGER default 0), `isbn` (TEXT default ''). Case-insensitive index `idx_books_author` on `author`.

## Library API

`NewStore(dsn) (*Store, error)`; `Store.{Create, List(author), Get(id), Update(id,b), Delete(id), Ping, Close}`; `NewHandler(store) http.Handler`.
