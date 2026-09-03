# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` | `main.go:healthHandler` |
| POST | /books | `201 Book` / `400` | `main.go:createBookHandler` |
| GET | /books | `200 [Book]` (optional `?author=`) | `main.go:getBooksHandler` |
| GET | /books/{id} | `200 Book` / `404` | `main.go:getBookByIdHandler` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `main.go:updateBookHandler` |
| DELETE | /books/{id} | `200 {message}` / `404` | `main.go:deleteBookHandler` |

Routing: `/books` and `/books/` are registered separately; `singleBookHandler` parses the id from the path via `strconv.Atoi`, returning `400` on a non-numeric id.

## Data schema

`books` table (SQLite, `./books.db`): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## CLI / Library API

(none) — server binary only. Port from `PORT` env var, default `8080`.
