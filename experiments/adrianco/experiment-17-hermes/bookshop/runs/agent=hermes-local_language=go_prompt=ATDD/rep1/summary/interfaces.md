# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201 Book` / `400` | `handlers.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `handlers.go:getBooks` |
| GET | /books/{id} | `200 Book` / `404` / `400` | `handlers.go:getBook` |
| PUT | /books/{id} | `200 Book` / `400` / `500` | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204` / `404` / `400` | `handlers.go:deleteBook` |
| GET | /health | `200 {"status":"healthy"}` | `router.go` inline |

## Data schema

`books` table (SQLite, `./books.db`): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

`Book` JSON: `{id, title, author, year, isbn}`.

## CLI commands

(none)

## Library API

(none — `package main`, not importable)
