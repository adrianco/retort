# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `main.go` inline closure |
| POST | /books | `201 Book` (+ `Location`) / `400` | `main.go:handlers.create` |
| GET | /books | `200 [Book]` (optional `?author=`) | `main.go:handlers.list` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `main.go:handlers.get` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `main.go:handlers.update` |
| DELETE | /books/{id} | `204` / `404` / `400` | `main.go:handlers.delete` |

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL DEFAULT 0), `isbn` (TEXT NOT NULL DEFAULT '').

## Library API

- `NewServer(s *Store) http.Handler` — builds the mux.
- `NewStore(dsn string) (*Store, error)` — opens DB and ensures schema.
- `Store.Create/List/Get/Update/Delete` — CRUD over `Book`.
