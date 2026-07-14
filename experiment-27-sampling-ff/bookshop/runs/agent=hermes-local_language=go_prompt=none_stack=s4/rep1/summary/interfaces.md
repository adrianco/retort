# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.go:healthHandler` |
| POST | /books | `201 Book \| 400` | `app.go:createBookHandler` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.go:listBooksHandler` |
| GET | /books/:id | `200 Book \| 400 \| 404` | `app.go:getBookHandler` |
| PUT | /books/:id | `200 Book \| 400 \| 404` | `app.go:updateBookHandler` |
| DELETE | /books/:id | `200 {message} \| 400 \| 404` | `app.go:deleteBookHandler` |

Server listens on `:8080`.

## Request bodies

- `CreateBookRequest`: `title` (required), `author` (required), `year`, `isbn`.
- `UpdateBookRequest`: `title`, `author`, `year`, `isbn` (all optional; empty/zero values fall back to existing stored values — partial update).

## Data schema

`books` table (SQLite, `./books.db`):

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| title | TEXT | NOT NULL |
| author | TEXT | NOT NULL |
| year | INTEGER | |
| isbn | TEXT | |

## CLI commands

(none)

## Library API

(none — package `main`, not importable)
