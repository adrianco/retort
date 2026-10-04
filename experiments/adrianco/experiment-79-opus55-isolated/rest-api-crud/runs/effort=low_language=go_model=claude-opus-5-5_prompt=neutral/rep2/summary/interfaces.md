# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` / `503` | `handlers.go:health` |
| POST | /books | `201 Book` (+ Location) / `400` / `413` | `handlers.go:createBook` |
| GET | /books | `200 [Book]` (`?author=` filter, case-insensitive) | `handlers.go:listBooks` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `handlers.go:getBook` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204` / `400` / `404` | `handlers.go:deleteBook` |

Routing uses Go 1.22+ `http.ServeMux` method+path patterns; unmatched methods yield 405.

## Data schema

`books` table (SQLite via `modernc.org/sqlite`, pure-Go driver):
id (INTEGER pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL),
year (INTEGER default 0), isbn (TEXT default ''). Index `idx_books_author` on author.

## Library API

- `NewStore(dsn) (*Store, error)` — opens/creates DB (`:memory:` supported), `MaxOpenConns=1`.
- `Store` methods: `Create`, `List(author)`, `Get(id)`, `Update`, `Delete`, `Ping`, `Close`.
- `NewHandler(*Store) http.Handler` — the wired router.
