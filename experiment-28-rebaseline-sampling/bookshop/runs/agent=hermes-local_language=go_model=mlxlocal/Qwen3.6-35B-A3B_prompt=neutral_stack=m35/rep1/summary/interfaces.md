# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.go:healthHandler` |
| POST | /books | `201 Book \| 400` | `app.go:createBookHandler` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.go:listBooksHandler` |
| GET | /books/:id | `200 Book \| 404 \| 400` | `app.go:getBookHandler` |
| PUT | /books/:id | `200 Book \| 404 \| 400` | `app.go:updateBookHandler` |
| DELETE | /books/:id | `200 {message} \| 404 \| 400` | `app.go:deleteBookHandler` |

## Data schema

`books` table: id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER NOT NULL), isbn (TEXT NOT NULL).

## CLI commands / Library API

(none)
