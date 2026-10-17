# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` / `503` | `server.go:handleHealth` |
| POST | /books | `201 Book` (+ Location) / `400` / `409` | `server.go:handleCreate` |
| GET | /books | `200 [Book]` | `server.go:handleList` (supports `?author=`) |
| GET | /books/{id} | `200 Book` / `400` / `404` | `server.go:handleGet` |
| PUT | /books/{id} | `200 Book` / `400` / `404` / `409` | `server.go:handleUpdate` |
| DELETE | /books/{id} | `204` / `400` / `404` | `server.go:handleDelete` |

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null),
year (INTEGER default 0), isbn (TEXT default ''). Index on `author` (NOCASE);
partial unique index on `isbn` where `isbn <> ''`.

## Exported API (package-internal)

`OpenStore(path)`, `Store` CRUD methods, `NewServer(store)`, `BookInput.Validate()`.
