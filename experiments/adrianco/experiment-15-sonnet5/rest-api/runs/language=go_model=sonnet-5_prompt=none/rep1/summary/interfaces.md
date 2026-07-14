# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `handlers.go:handleHealth` |
| POST | /books | `201 Book \| 400` | `handlers.go:handleCreate` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `handlers.go:handleList` |
| GET | /books/{id} | `200 Book \| 400 \| 404` | `handlers.go:handleGet` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `handlers.go:handleUpdate` |
| DELETE | /books/{id} | `204 \| 400 \| 404` | `handlers.go:handleDelete` |

## Data schema

`books` table: id (INTEGER, pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).

## Library API

- `NewStore(dsn string) (*Store, error)` — opens and migrates a SQLite DB.
- `NewAPI(store *Store) *API` / `(*API).Routes() http.Handler` — builds the mux.
- `Book.Validate() error` — enforces required title/author.
