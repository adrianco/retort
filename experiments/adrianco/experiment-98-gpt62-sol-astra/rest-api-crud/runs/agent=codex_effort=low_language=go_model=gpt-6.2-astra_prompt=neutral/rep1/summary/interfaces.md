# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201 Book` + `Location` header | `main.go:api.save` (id=0) |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `main.go:api.list` |
| GET | /books/{id} | `200 Book \| 404` | `main.go:api.ServeHTTP` |
| PUT | /books/{id} | `200 Book \| 404` | `main.go:api.save` (id>0) |
| DELETE | /books/{id} | `204 \| 404` | `main.go:api.ServeHTTP` |
| GET | /health | `200 {status:ok} \| 503` | `main.go:api.ServeHTTP` |

Unknown routes return `404`; unsupported methods return `405` with an `Allow` header. Errors return a JSON `{"error": ...}` body.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT NOT NULL).

JSON `Book`: `{id, title, author, year (nullable int), isbn}`.
