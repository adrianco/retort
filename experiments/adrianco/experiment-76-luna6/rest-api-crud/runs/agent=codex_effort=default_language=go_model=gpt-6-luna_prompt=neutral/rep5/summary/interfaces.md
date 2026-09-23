# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} 200` | `handler.go:health` |
| POST | /books | `Book 201 \| 400` | `handler.go:books` |
| GET | /books | `[Book] 200` (opt `?author=`) | `handler.go:books` |
| GET | /books/{id} | `Book 200 \| 404 \| 400` | `handler.go:book` |
| PUT | /books/{id} | `Book 200 \| 404 \| 400` | `handler.go:book` |
| DELETE | /books/{id} | `204 \| 404 \| 400` | `handler.go:book` |

Unsupported methods on a matched path return `405` via `methodNotAllowed`.

## Data schema

`books` table (SQLite, `modernc.org/sqlite`): `id` (INTEGER PK AUTOINCREMENT),
`title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0),
`isbn` (TEXT DEFAULT '').

## Library API

`newHandler(db *sql.DB) http.Handler` — wires the mux; `bookStore` methods
`list/get/create/update/delete`; `validateBook(Book) error`.
