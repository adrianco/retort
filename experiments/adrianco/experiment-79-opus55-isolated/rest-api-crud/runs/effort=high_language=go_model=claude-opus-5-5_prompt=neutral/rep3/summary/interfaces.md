# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status} \| 503` | `handlers.go:handleHealth` |
| POST | /books | `201 Book + Location \| 400 \| 413` | `handlers.go:handleCreateBook` |
| GET | /books | `200 [Book]` (optional `?author=`) | `handlers.go:handleListBooks` |
| GET | /books/{id} | `200 Book \| 400 \| 404` | `handlers.go:handleGetBook` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `handlers.go:handleUpdateBook` |
| DELETE | /books/{id} | `204 \| 400 \| 404` | `handlers.go:handleDeleteBook` |

Unsupported method/path combinations return `405` (with an `Allow` header) or `404`,
always in JSON.

## Data schema

`books` table (store.go:25): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER NOT NULL DEFAULT 0), `isbn` (TEXT NOT NULL
DEFAULT ''). Case-insensitive index `idx_books_author` on `author`.

## Library API (package main)

- `OpenStore(ctx, path) (*Store, error)` — opens/creates the SQLite DB, applies schema.
- `(*Store)` methods: `Create`, `List(author)`, `Get`, `Update`, `Delete`, `Ping`, `Close`.
- `NewServer(store, logger).Routes() http.Handler` — the composed HTTP handler.
