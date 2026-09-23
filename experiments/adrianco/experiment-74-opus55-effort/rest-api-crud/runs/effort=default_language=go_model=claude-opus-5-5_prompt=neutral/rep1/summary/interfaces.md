# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `handlers.go:health` |
| POST | /books | `Book (201)` + Location header | `handlers.go:createBook` |
| GET | /books | `[Book] (200)`, `?author=` filter | `handlers.go:listBooks` |
| GET | /books/{id} | `Book (200) \| 404 \| 400` | `handlers.go:getBook` |
| PUT | /books/{id} | `Book (200) \| 404 \| 400` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204 \| 404 \| 400` | `handlers.go:deleteBook` |

Routing uses Go 1.22 `net/http.ServeMux` method+pattern matching; unmatched methods yield 405.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER default 0), isbn (TEXT default '').

## Validation

`bookInput.validate()`: title & author required (trimmed); year in [0, next year]; isbn optional but must be 10/13 digits (hyphens/spaces allowed, ISBN-10 trailing X). Decoder uses `DisallowUnknownFields` + 1 MiB body cap.
