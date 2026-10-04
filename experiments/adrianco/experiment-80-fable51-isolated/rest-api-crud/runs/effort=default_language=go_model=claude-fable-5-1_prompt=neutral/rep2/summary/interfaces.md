# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `handlers.go:health` |
| POST | /books | `Book` 201 (+ Location) | `handlers.go:createBook` |
| GET | /books | `[Book]` 200 (`?author=` exact, case-insensitive filter) | `handlers.go:listBooks` |
| GET | /books/{id} | `Book` 200 / 404 | `handlers.go:getBook` |
| PUT | /books/{id} | `Book` 200 / 404 | `handlers.go:updateBook` |
| DELETE | /books/{id} | 204 / 404 | `handlers.go:deleteBook` |

Error responses are JSON `{"error": "..."}`. Validation failures return 422 with a
`fields` map; malformed JSON or a non-positive `{id}` returns 400; oversized bodies 413.

## Data schema

`books` table (SQLite): `id` (INTEGER pk autoincrement), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER default 0), `isbn` (TEXT default '').
Index `idx_books_author` on `author`.

## Library API

`Store` — `Create`, `List(author)`, `Get`, `Update`, `Delete`, `Ping`, `Close`.
`NewHandler(store) http.Handler` — the wired router.
