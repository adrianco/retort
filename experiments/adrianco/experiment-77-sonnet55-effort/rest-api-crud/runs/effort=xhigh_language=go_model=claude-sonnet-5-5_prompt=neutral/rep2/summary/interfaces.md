# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` / `503` | `api.go:server.health` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `api.go:server.listBooks` |
| POST | /books | `201 Book` + `Location` header / `400` | `api.go:server.createBook` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `api.go:server.getBook` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `api.go:server.updateBook` |
| DELETE | /books/{id} | `204` / `400` / `404` | `api.go:server.deleteBook` |

Unmatched methods on a known path return `405` with an `Allow` header; unknown
paths return a JSON `404`. `HEAD` is served like `GET`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL COLLATE NOCASE), `year` (INTEGER, nullable),
`isbn` (TEXT NOT NULL DEFAULT ''). Index `idx_books_author` on `author`.

## Library API

`store.Store` exposes `Create/Get/List/Update/Delete/Ping/Close`; `api.New(BookStore, *slog.Logger)` returns an `http.Handler`.
