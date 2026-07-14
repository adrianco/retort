# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status}` | `app.go:healthHandler` |
| POST | /books | `Book` (201) / 400 | `app.go:createBookHandler` |
| GET | /books | `[Book]` (200), `?author=` filter | `app.go:listBooksHandler` |
| GET | /books/:id | `Book` (200) / 404 | `app.go:getBookHandler` |
| PUT | /books/:id | `Book` (200) / 404 / 400 | `app.go:updateBookHandler` |
| DELETE | /books/:id | `{message}` (200) / 404 | `app.go:deleteBookHandler` |

## Data schema

`books` table (SQLite, `./books.db`): id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).

## Request bodies

- `CreateBookRequest`: title (required), author (required), year, isbn — validated via Gin `binding:"required"`.
- `UpdateBookRequest`: title, author, year, isbn — all optional; empty/zero fields fall back to existing values (partial update).

## CLI commands

(none)

## Library API

(none — `package main`, not importable)
