# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `handlers.go:health` |
| POST | /books | `Book` 201 / 400 | `handlers.go:createBook` |
| GET | /books | `[Book]` 200 (opt. `?author=`) | `handlers.go:listBooks` |
| GET | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:getBook` |
| PUT | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:updateBook` |
| DELETE | /books/{id} | 204 / 404 / 400 | `handlers.go:deleteBook` |

Routing uses Go 1.22+ `net/http` method+path patterns (`GET /books/{id}`), no third-party router. Errors are JSON `{"error": "..."}`.

## Data schema

`books` table: id (INTEGER pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER default 0), isbn (TEXT default '').

## Library API

`NewStore(dsn) -> *Store` with `Create`, `List(author)`, `Get(id)`, `Update`, `Delete`, `Ping`, `Close`. `:memory:` DSN supported for tests.
