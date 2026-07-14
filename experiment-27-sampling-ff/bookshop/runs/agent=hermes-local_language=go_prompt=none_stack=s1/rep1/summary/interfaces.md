# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `app.go:healthCheck` |
| POST | /books | `201 Book \| 400` | `app.go:createBook` |
| GET | /books | `200 [Book]` (opt `?author=` filter) | `app.go:listBooks` |
| GET | /books/:id | `200 Book \| 400 \| 404` | `app.go:getBook` |
| PUT | /books/:id | `200 Book \| 400 \| 404` | `app.go:updateBook` |
| DELETE | /books/:id | `200 {message} \| 400 \| 404` | `app.go:deleteBook` |

## CLI commands

(none)

## Library API

(none — `package main`, no exported package surface)

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER NOT NULL), `isbn` (TEXT NOT NULL). Stored in `./books.db` (SQLite via `mattn/go-sqlite3`).
