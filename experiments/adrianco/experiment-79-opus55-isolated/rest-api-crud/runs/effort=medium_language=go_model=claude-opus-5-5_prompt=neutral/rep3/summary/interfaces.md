# Interfaces

## HTTP routes

Routed with Go 1.22+ `net/http` method-and-pattern `ServeMux` (`handlers.go:23-30`).

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `handlers.go:health` |
| POST | /books | `Book` 201 (+ `Location`) / 400 | `handlers.go:createBook` |
| GET | /books | `[Book]` 200 (`?author=` filter) | `handlers.go:listBooks` |
| GET | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:getBook` |
| PUT | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:updateBook` |
| DELETE | /books/{id} | 204 / 404 / 400 | `handlers.go:deleteBook` |

Unmatched method on a known path yields 405 (ServeMux default).

## Data schema

`books` table (`store.go:28-36`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL),
author (TEXT NOT NULL), year (INTEGER NOT NULL DEFAULT 0), isbn (TEXT NOT NULL DEFAULT '').
Index `idx_books_author` on author for the filter query.

## Exported library API

`NewStore(dsn)`, `Store` (`Create`/`List`/`Get`/`Update`/`Delete`/`Ping`/`Close`),
`NewHandler(store)`, `Book`, `ErrNotFound`.
