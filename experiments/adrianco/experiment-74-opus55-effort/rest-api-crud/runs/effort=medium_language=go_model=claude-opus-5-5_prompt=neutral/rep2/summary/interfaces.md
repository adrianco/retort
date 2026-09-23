# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `handlers.go:health` |
| POST | /books | `Book` 201 (+ `Location`) \| 400 \| 422 | `handlers.go:createBook` |
| GET | /books | `[Book]` 200, optional `?author=` (exact, case-insensitive) | `handlers.go:listBooks` |
| GET | /books/{id} | `Book` 200 \| 404 \| 400 | `handlers.go:getBook` |
| PUT | /books/{id} | `Book` 200 \| 404 \| 400 \| 422 | `handlers.go:updateBook` |
| DELETE | /books/{id} | 204 \| 404 \| 400 | `handlers.go:deleteBook` |

## Data schema

`books` table (SQLite via `modernc.org/sqlite`): id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER default 0), isbn (TEXT default '').

## Library API

`OpenStore(dsn) (*Store, error)` and `Store.Create/List/Get/Update/Delete/Ping/Close`; `Book` domain struct; `ErrNotFound` sentinel.
