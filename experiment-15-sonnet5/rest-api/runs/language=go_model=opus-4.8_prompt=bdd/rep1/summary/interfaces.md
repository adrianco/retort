# Interfaces

## HTTP routes

Routed via Go 1.22+ `net/http.ServeMux` method+path patterns (`server.go:routes`).

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` (200) | `server.go:handleHealth` |
| POST | /books | `Book` (201) / `{"error"}` (400) | `server.go:handleCreate` |
| GET | /books | `[Book]` (200), optional `?author=` filter | `server.go:handleList` |
| GET | /books/{id} | `Book` (200) / 404 | `server.go:handleGet` |
| PUT | /books/{id} | `Book` (200) / 400 / 404 | `server.go:handleUpdate` |
| DELETE | /books/{id} | (204) / 404 | `server.go:handleDelete` |

## Library API

- `NewStore(dsn string) (*Store, error)` — opens SQLite, runs migration.
- `Store.Create/List/Get/Update/Delete` — CRUD, returning `ErrNotFound` where applicable.
- `NewServer(store *Store) *Server` — wires routes; `Server` implements `http.Handler`.

## Data schema

`books` table (`store.go:migrate`):

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PK, AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | NOT NULL |
| isbn | TEXT | NOT NULL |
