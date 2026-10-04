# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` / `503` | `handlers.go:Server.health` |
| POST | /books | `201` + Book (+ `Location`) | `handlers.go:Server.createBook` |
| GET | /books | `200` + `[Book]`; `?author=` filters | `handlers.go:Server.listBooks` |
| GET | /books/{id} | `200` + Book / `404` | `handlers.go:Server.getBook` |
| PUT | /books/{id} | `200` + Book / `404` | `handlers.go:Server.updateBook` |
| DELETE | /books/{id} | `204` / `404` | `handlers.go:Server.deleteBook` |

Routing uses Go 1.22+ method-pattern `ServeMux` (`"GET /books/{id}"`), so an
unmatched method (e.g. PATCH) yields `405 Method Not Allowed` automatically.

## Error responses

| Status | When |
|--------|------|
| `400` | Malformed JSON, wrong field type, unknown field, empty body, bad `{id}` |
| `404` | No book with that ID |
| `413` | Request body larger than 1 MiB |
| `422` | Validation failed (missing/blank title or author, negative year) |

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').
Index `idx_books_author` on `author`.

## Library API (package main)

`NewStore(dsn) (*Store, error)`, `Store.{Create,List,Get,Update,Delete,Ping,Close}`,
`NewHandler(*Store) http.Handler`, `Book`, `ErrNotFound`.
