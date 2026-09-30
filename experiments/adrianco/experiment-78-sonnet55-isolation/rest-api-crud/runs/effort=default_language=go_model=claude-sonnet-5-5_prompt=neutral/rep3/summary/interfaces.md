# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 200/503` | `main.go` inline (Handler) |
| POST | /books | `Book \| 201/400/500` | `main.go:Server.create` |
| GET | /books | `[Book] \| 200` (optional `?author=` exact filter) | `main.go:Server.list` |
| GET | /books/{id} | `Book \| 200/400/404` | `main.go:Server.get` |
| PUT | /books/{id} | `Book \| 200/400/404` | `main.go:Server.update` |
| DELETE | /books/{id} | `204/400/404` | `main.go:Server.remove` |

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER default 0), isbn (TEXT default '').

## Config

Env vars: `ADDR` (default `:8080`), `DB_PATH` (default `books.db`).
