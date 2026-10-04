# Interfaces

## HTTP routes

Routes are registered with Go 1.22+ method-aware `http.ServeMux` patterns (`main.go:66-80`).

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` \| 503 | `main.go:Handler` (inline) |
| POST | /books | `Book` (201) \| 400 | `main.go:createBook` |
| GET | /books | `[Book]` (200), `?author=` filter | `main.go:listBooks` |
| GET | /books/{id} | `Book` (200) \| 404 \| 400 | `main.go:getBook` |
| PUT | /books/{id} | `Book` (200) \| 404 \| 400 | `main.go:updateBook` |
| DELETE | /books/{id} | 204 \| 404 \| 400 | `main.go:deleteBook` |

## Data schema

`books` table (`main.go:50-56`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL),
author (TEXT NOT NULL), year (INTEGER NOT NULL DEFAULT 0), isbn (TEXT NOT NULL DEFAULT '').

## Library API

- `OpenDB(dsn string) (*sql.DB, error)` — opens SQLite and creates the schema.
- `NewServer(db *sql.DB) *Server` / `Server.Handler() http.Handler` — construct the mux.
