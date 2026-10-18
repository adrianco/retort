# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `main.go:ServeHTTP` |
| POST | /books | `201 Book` / `400` | `main.go:createBook` |
| GET | /books | `200 [Book]` (opt `?author=`) | `main.go:listBooks` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `main.go:bookByID` |
| PUT | /books/{id} | `200 Book` / `404` / `400` | `main.go:bookByID` |
| DELETE | /books/{id} | `204` / `404` | `main.go:bookByID` |

Unsupported methods on a known path return `405`. Unknown paths return `404`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').

Driver: pure-Go `modernc.org/sqlite`. DB path from `BOOKS_DB` env (default `books.db`); `:memory:` used in tests.

## CLI commands

(none)

## Library API

`API` struct wraps `*sql.DB` and implements `http.Handler`.
