# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` / `503` | `handlers.go:health` |
| POST | /books | `201 Book` / `400` | `handlers.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=`) | `handlers.go:listBooks` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `handlers.go:getBook` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204` / `404` / `400` | `handlers.go:deleteBook` |

Uses Go 1.22 `net/http` method+path-pattern routing (`mux.HandleFunc("GET /books/{id}", ...)`); no third-party web framework. Create sets a `Location` header.

## Data schema

`books` table (SQLite via `modernc.org/sqlite`, pure-Go driver):
id (INTEGER pk autoincrement), title (TEXT not null), author (TEXT not null), year (INTEGER default 0), isbn (TEXT default '').

## Library API

- `OpenStore(dsn)` — opens/creates DB, applies schema, `:memory:` pins to one conn.
- `BookInput.Validate()` — returns field→problem map; title/author required, year 1450..now+1, ISBN-10/13 checksum.
