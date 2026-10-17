# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `api.go:handleHealth` |
| POST | /books | `Book` (201, Location header) | `api.go:handleCreate` |
| GET | /books | `[Book]` (200), `?author=` filter | `api.go:handleList` |
| GET | /books/{id} | `Book` (200) \| 404 | `api.go:handleGet` |
| PUT | /books/{id} | `Book` (200) \| 404 | `api.go:handleUpdate` |
| DELETE | /books/{id} | 204 \| 404 | `api.go:handleDelete` |

Error codes: 400 (malformed JSON / non-positive id), 404 (not found),
422 (validation failed, with a `fields` map), 500 (server/db error).

## Data schema

`books` table: `id` (int pk autoincrement), `title` (text not null),
`author` (text not null), `year` (int default 0), `isbn` (text default '').
Case-insensitive index on `author`.
