# Interfaces

## HTTP routes

Routes are registered with Go 1.22+ method-prefixed `ServeMux` patterns in `handlers.go:NewHandler`.

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `handlers.go:api.health` |
| POST | /books | `201 Book` + `Location` header / `400` | `handlers.go:api.create` |
| GET | /books | `200 [Book]` (supports `?author=` filter) | `handlers.go:api.list` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `handlers.go:api.get` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `handlers.go:api.update` |
| DELETE | /books/{id} | `204` / `400` / `404` | `handlers.go:api.delete` |

Errors return JSON `{"error": "<msg>"}`. `500` on unexpected store errors.

## Library API

- `NewStore(dsn string) (*Store, error)` — opens SQLite, creates schema, caps to 1 open connection.
- `Store` methods: `Create(*Book)`, `List(author string) ([]Book, error)`, `Get(id int64) (*Book, error)`, `Update(*Book)`, `Delete(id int64)`, `Close()`.
- `NewHandler(s *Store) http.Handler` — builds the router.
- Sentinel `errNotFound` maps to HTTP 404 via `api.fail`.

## Data schema

`books` table (SQLite, via `modernc.org/sqlite`, pure-Go driver):

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | NOT NULL DEFAULT 0 |
| isbn | TEXT | NOT NULL DEFAULT '' |

JSON `Book`: `id`, `title`, `author`, `year`, `isbn`.

## Validation rules (`handlers.go:decode`)

- `title` and `author` required (trimmed, non-empty).
- `year` must not be negative.
- Request body capped at 1 MiB (`http.MaxBytesReader`).
- Malformed JSON and non-numeric/`< 1` IDs return `400`.

## CLI commands

(none — configuration is via `ADDR` and `DB_PATH` environment variables.)
