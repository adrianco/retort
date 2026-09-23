# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `main.go:ServeHTTP` |
| POST | /books | `201 Book \| 400` | `main.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=`) | `main.go:listBooks` |
| GET | /books/{id} | `200 Book \| 404 \| 400` | `main.go:getBook` |
| PUT | /books/{id} | `200 Book \| 404 \| 400` | `main.go:updateBook` |
| DELETE | /books/{id} | `204 \| 404 \| 400` | `main.go:deleteBook` |

Unsupported methods on a known path return `405` with an `Allow` header.

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER default 0), `isbn` (TEXT default '').

## Library API

`NewAPI(db *sql.DB) (*API, error)` — constructs the handler and creates the table. `API` implements `http.Handler`.
