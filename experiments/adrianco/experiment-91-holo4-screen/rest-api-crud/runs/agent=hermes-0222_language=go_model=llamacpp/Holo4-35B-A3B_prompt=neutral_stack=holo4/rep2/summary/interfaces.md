# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:"ok"}` | `handler.go:healthHandler` |
| POST | /books | `201 Book \| 400 \| 409` | `handler.go:createBook` |
| GET | /books | `200 [Book]` (optional `?author=`) | `handler.go:listBooks` |
| GET | /books/{id} | `200 Book \| 404` | `handler.go:getBook` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `handler.go:updateBook` |
| DELETE | /books/{id} | `204 \| 404` | `handler.go:deleteBook` |

Routing is method-switched inside two handlers registered on `/books` and
`/books/`; unsupported methods return `405`.

## Data schema

`books` table (SQLite, `modernc.org/sqlite` — pure-Go driver):
id (INTEGER pk autoincrement), title (TEXT NOT NULL), author (TEXT NOT NULL),
year (INTEGER NOT NULL), isbn (TEXT UNIQUE NOT NULL).

## Library API

(none — single `package main`, no exported library surface.)

## CLI commands

(none — `PORT` env var selects the listen port, default 8000.)
