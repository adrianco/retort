# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status,database}` \| 503 | `api.go:health` |
| POST | /books | `201 Book` (+ Location) \| 409 \| 415 \| 400 \| 422 | `api.go:createBook` |
| GET | /books | `200 {books,count}` (optional `?author=` filter) | `api.go:listBooks` |
| GET | /books/{id} | `200 Book` \| 404 \| 400 | `api.go:getBook` |
| PUT | /books/{id} | `200 Book` \| 404 \| 409 \| 400 \| 422 | `api.go:updateBook` |
| DELETE | /books/{id} | `204` \| 404 \| 400 | `api.go:deleteBook` |

Unmatched routes and methods are rewritten from the mux's plain-text 404/405
into the JSON error shape by `routerErrorWriter`.

## Data schema

`books` table (SQLite):
`id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL),
`year` (INTEGER NOT NULL DEFAULT 0), `isbn` (TEXT NOT NULL DEFAULT ''),
`created_at` (TEXT), `updated_at` (TEXT).
Partial unique index on `isbn` where `isbn <> ''`; case-insensitive index on `author`.

## Error shape

`{"error": string, "fields": {field: message}}` — `fields` omitted when empty.

## CLI / config

No CLI subcommands. Runtime config via env: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`; `:memory:` supported).
