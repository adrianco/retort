# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` \| 503 | `server.go:health` |
| POST | /books | `Book` (201) \| 400 | `server.go:create` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `server.go:list` |
| GET | /books/{id} | `Book` (200) \| 404 \| 400 | `server.go:get` |
| PUT | /books/{id} | `Book` (200) \| 404 \| 400 | `server.go:update` |
| DELETE | /books/{id} | 204 \| 404 \| 400 | `server.go:delete` |

Errors return `{"error": "..."}` with 400/404/500/503.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT). Backed by `modernc.org/sqlite` (pure-Go, no cgo); `db.SetMaxOpenConns(1)` serializes writes.

## Library API

`NewServer(db *sql.DB) (*Server, error)` — creates the table and wires the `http.ServeMux`. `Server` implements `http.Handler`.
