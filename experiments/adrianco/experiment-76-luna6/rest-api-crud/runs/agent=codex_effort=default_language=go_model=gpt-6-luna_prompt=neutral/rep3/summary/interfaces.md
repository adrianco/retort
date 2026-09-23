# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `{status} \| 503` | `main.go:API.ServeHTTP` (db.Ping) |
| POST | /books | `Book (201) \| 400 \| 500` | `main.go:API.collection` → `book.go:createBook` |
| GET | /books | `[Book] (200)` | `main.go:API.collection` → `book.go:listBooks` |
| GET | /books?author= | `[Book] (200)` filtered | `main.go:API.collection` → `book.go:listBooks` |
| GET | /books/{id} | `Book \| 404 \| 400` | `main.go:API.item` → `book.go:getBook` |
| PUT | /books/{id} | `Book \| 404 \| 400` | `main.go:API.item` → `book.go:updateBook` |
| DELETE | /books/{id} | `204 \| 404 \| 400` | `main.go:API.item` → `book.go:deleteBook` |

Method mismatches return `405` with an `Allow` header.

## Data schema

`books` table: `id` (INTEGER pk autoincrement), `title` (TEXT not null), `author` (TEXT not null), `year` (INTEGER default 0), `isbn` (TEXT default '').

## Library API

Exported: `Book` struct; data-layer functions `openDatabase`, `createBook`, `getBook`, `listBooks`, `updateBook`, `deleteBook`; sentinel `ErrNotFound`.
