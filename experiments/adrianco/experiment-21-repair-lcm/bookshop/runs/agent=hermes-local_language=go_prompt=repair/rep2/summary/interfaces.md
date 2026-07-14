# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `handlers.go:healthCheck` |
| POST | /books | `201 Book \| 400` | `handlers.go:createBook` |
| GET | /books?author= | `200 [Book]` | `handlers.go:listBooks` |
| GET | /books/{id} | `200 Book \| 400 \| 404` | `handlers.go:getBook` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204 \| 400 \| 404` | `handlers.go:deleteBook` |

Routing is done with two `ServeMux` patterns (`/books` and `/books/`), dispatching by `r.Method` inside anonymous funcs in `main.go`. Unsupported methods return `405`. Path IDs are parsed by trimming the `/books/` prefix.

## Data schema

`books` table (SQLite, `modernc.org/sqlite`):

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | NOT NULL |
| isbn | TEXT | NOT NULL |

## Library API

`BookRepository` interface: `CreateBook`, `ListBooks(authorFilter *string)`, `GetBook`, `UpdateBook(id, UpdateBookRequest)`, `DeleteBook`. Implemented by `SQLiteRepo`. `UpdateBookRequest` uses pointer fields for partial updates.

## CLI commands

(none) — server configured via `PORT` env var (default `8080`) and a fixed `books.db` file.
