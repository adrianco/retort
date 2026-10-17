# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` / `503` | `handlers.go:handleHealth` |
| POST | /books | `201 Book` (+ Location) / `422` / `400` / `409` | `handlers.go:handleCreate` |
| GET | /books | `200 [Book]` (`?author=` filter) | `handlers.go:handleList` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `handlers.go:handleGet` |
| PUT | /books/{id} | `200 Book` / `404` / `422` / `409` | `handlers.go:handleUpdate` |
| DELETE | /books/{id} | `204` / `404` / `400` | `handlers.go:handleDelete` |

Routing uses Go 1.22+ `net/http.ServeMux` method+path patterns; unmatched methods yield 405.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null),
year (INTEGER default 0), isbn (TEXT default ''). Index on author; partial unique index on
isbn where isbn <> ''.

## Library API

Exported: `Store` (+ CRUD methods, `Ping`), `OpenStore`, `NewServer`, `Book`, `BookInput`,
`ValidationErrors`, sentinels `ErrNotFound` / `ErrISBNTaken`.
