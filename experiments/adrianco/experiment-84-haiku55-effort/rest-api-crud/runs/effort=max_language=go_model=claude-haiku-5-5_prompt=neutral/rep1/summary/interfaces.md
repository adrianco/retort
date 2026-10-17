# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` / `503 {status:unavailable}` | `api.go:health` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `api.go:listBooks` |
| POST | /books | `201 Book` + `Location` header / `400` | `api.go:createBook` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `api.go:getBook` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `api.go:updateBook` |
| DELETE | /books/{id} | `204` / `400` / `404` | `api.go:deleteBook` |

Unlisted methods on a known path return `405` with an `Allow` header; unknown paths return a JSON `404`. HEAD is served by the GET handler.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Error body

`{"error": string, "fields": {field: message}}` — `fields` present only on validation failures.
