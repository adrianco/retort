# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` 200 / 503 | `handlers.go:Server.health` |
| POST | /books | `Book` 201 / 400 | `handlers.go:Server.createBook` |
| GET | /books | `[Book]` 200 (`?author=` exact, case-insensitive) | `handlers.go:Server.listBooks` |
| GET | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:Server.getBook` |
| PUT | /books/{id} | `Book` 200 / 404 / 400 | `handlers.go:Server.updateBook` |
| DELETE | /books/{id} | 204 / 404 / 400 | `handlers.go:Server.deleteBook` |

Routing uses Go 1.22+ `net/http` method+path patterns (`GET /books/{id}`), so a
wrong method on a known path yields 405 automatically.

## Library API

- `store.OpenStore(dsn) (*Store, error)` — open/create SQLite DB, ensure schema
- `Store.Create/List(author)/Get(id)/Update/Delete(id)` — CRUD, `ErrNotFound` sentinel
- `Server.Routes() http.Handler` — assembled mux

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER NOT NULL DEFAULT 0),
`isbn` (TEXT NOT NULL DEFAULT '').
