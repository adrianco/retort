# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `main.go:ServeHTTP` |
| POST | /books | `201 Book \| 400` | `main.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `main.go:listBooks` |
| GET | /books/{id} | `200 Book \| 404` | `main.go:getBook` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `main.go:updateBook` |
| DELETE | /books/{id} | `204 \| 404` | `main.go:deleteBook` |

Unmatched methods on a known path return `405`; unknown paths return `404`.

## Data schema

`books` table (SQLite via `modernc.org/sqlite`, pure-Go driver):
id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL),
year (INTEGER NOT NULL DEFAULT 0), isbn (TEXT NOT NULL DEFAULT '').

## Library API

`Book` struct, `API` type, `NewAPI(*sql.DB)`, `openDB(dsn)`, and an unused
`API.ping(ctx)` readiness helper.
