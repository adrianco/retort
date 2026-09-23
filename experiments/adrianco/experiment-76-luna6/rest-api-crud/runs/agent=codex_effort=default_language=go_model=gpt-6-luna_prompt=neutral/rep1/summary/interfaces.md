# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{"status":"ok"}` \| 503 | `main.go:health` |
| POST | /books | `Book` (201) \| 400 | `main.go:createBook` |
| GET | /books | `[Book]` (200), `?author=` filter | `main.go:listBooks` |
| GET | /books/{id} | `Book` (200) \| 404 \| 400 | `main.go:book` |
| PUT | /books/{id} | `Book` (200) \| 404 \| 400 | `main.go:book` |
| DELETE | /books/{id} | 204 \| 404 \| 400 | `main.go:book` |

Routing uses `net/http.ServeMux`: `GET /health` (Go 1.22 method pattern), `/books` and
`/books/` dispatch on `r.Method` inside the handler.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER NOT NULL DEFAULT 0), `isbn` (TEXT NOT NULL DEFAULT '').
