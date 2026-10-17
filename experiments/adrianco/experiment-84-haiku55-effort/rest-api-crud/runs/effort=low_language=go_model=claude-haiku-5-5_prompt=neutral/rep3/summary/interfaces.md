# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `server.go:handleHealth` |
| POST | /books | `Book 201 \| 400` | `server.go:handleCreate` |
| GET | /books | `[Book] 200` (optional `?author=`) | `server.go:handleList` |
| GET | /books/{id} | `Book 200 \| 404 \| 400` | `server.go:handleGet` |
| PUT | /books/{id} | `Book 200 \| 404 \| 400` | `server.go:handleUpdate` |
| DELETE | /books/{id} | `204 \| 404 \| 400` | `server.go:handleDelete` |

Routing uses Go 1.22+ `net/http.ServeMux` method+path-wildcard patterns.

## Data schema

`books` table (SQLite via `modernc.org/sqlite`, pure-Go driver):
id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL),
year (INTEGER NOT NULL DEFAULT 0), isbn (TEXT NOT NULL DEFAULT '').

## Library API

- `OpenStore(path) (*Store, error)` + `Store.{Create,Get,List,Update,Delete,Ping,Close}`
- `NewServer(*Store) *Server` implementing `http.Handler`

## Configuration (env)

- `ADDR` (default `:8080`), `DB_PATH` (default `books.db`)
