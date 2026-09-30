# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `handlers.go:api.health` |
| POST | /books | `Book` (201, `Location` header) | `handlers.go:api.create` |
| GET | /books | `[Book]` (optional `?author=` exact filter) | `handlers.go:api.list` |
| GET | /books/{id} | `Book \| 404 \| 400` | `handlers.go:api.get` |
| PUT | /books/{id} | `Book \| 404 \| 400` | `handlers.go:api.update` |
| DELETE | /books/{id} | 204 `\| 404 \| 400` | `handlers.go:api.delete` |

Errors are returned as `{"error": "message"}`. Routing uses the Go 1.22
`net/http.ServeMux` method+pattern syntax (`GET /books/{id}`).

## Data schema

`books` table (SQLite via `modernc.org/sqlite`, pure Go, no CGO):
id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null),
year (INTEGER default 0), isbn (TEXT default '').

## Library API

`Store` exposes `Create`, `Get`, `List(author)`, `Update`, `Delete`, `Ping`,
`Close`; `NewStore(dsn)` migrates on open (`:memory:` supported).
