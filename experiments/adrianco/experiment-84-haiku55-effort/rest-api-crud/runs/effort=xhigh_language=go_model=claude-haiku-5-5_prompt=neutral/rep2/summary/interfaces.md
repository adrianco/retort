# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` / `503` if DB ping fails | `server.go:health` |
| POST | /books | `201 Book` (+ `Location`) / `400` | `books.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `books.go:listBooks` |
| GET | /books/{id} | `200 Book` / `404` / `400` bad id | `books.go:getBook` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `books.go:updateBook` |
| DELETE | /books/{id} | `204` / `404` / `400` | `books.go:deleteBook` |
| (other methods on the above paths) | — | `405` + `Allow` header | `server.go:methodNotAllowed` |
| (any unmatched path) | — | `404 {error}` | `server.go:Handler` catch-all |

All responses are `application/json` except `204 No Content` on delete. Validation failures return `400` with `{"error":"validation failed","details":{field:msg}}`.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable). Case-insensitive index `idx_books_author` on `author`.

## Library API (internal)

- `book.Input.Normalize() / Validate() FieldErrors` — HTTP-agnostic validation; title & author required, optional year range and ISBN-10/13 check-digit validation.
- `store.Store` — `Open`, `Create`, `Get`, `List(author)`, `Update`, `Delete`, `Ping`, `Close`; returns `store.ErrNotFound`.

## CLI

`bookapi -addr :8080 -db books.db` — `-addr` listen address, `-db` SQLite file path.
