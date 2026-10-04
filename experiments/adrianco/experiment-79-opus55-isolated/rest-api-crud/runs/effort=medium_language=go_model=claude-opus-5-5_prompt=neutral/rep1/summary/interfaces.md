# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status} \| 503` | `handlers.go:handleHealth` |
| POST | /books | `201 Book \| 400 \| 413` | `handlers.go:handleCreate` |
| GET | /books | `200 [Book]` (optional `?author=`) | `handlers.go:handleList` |
| GET | /books/{id} | `200 Book \| 404 \| 400` | `handlers.go:handleGet` |
| PUT | /books/{id} | `200 Book \| 404 \| 400` | `handlers.go:handleUpdate` |
| DELETE | /books/{id} | `204 \| 404 \| 400` | `handlers.go:handleDelete` |

Unknown paths return `404` and unsupported methods `405`, both as JSON (`handlers.go:jsonErrors`).

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER default 0), isbn (TEXT default ''). Case-insensitive index on author (`store.go:schema`).
