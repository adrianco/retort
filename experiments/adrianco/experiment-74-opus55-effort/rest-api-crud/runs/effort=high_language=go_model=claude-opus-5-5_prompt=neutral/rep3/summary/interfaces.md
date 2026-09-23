# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{status,time}` / 503 if DB down | `handlers.go:health` |
| POST | /books | 201 `Book` (+ `Location` header) / 400 | `handlers.go:createBook` |
| GET | /books | 200 `[Book]` (`?author=` exact, case-insensitive filter) | `handlers.go:listBooks` |
| GET | /books/{id} | 200 `Book` / 404 / 400 bad id | `handlers.go:getBook` |
| PUT | /books/{id} | 200 `Book` / 404 / 400 | `handlers.go:updateBook` |
| DELETE | /books/{id} | 204 / 404 / 400 | `handlers.go:deleteBook` |

Unmatched methods on a known path return 405 (mux default for method patterns).

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT ''). Index `idx_books_author` on `author`.

## Exported Go API (package main)

`OpenStore(dsn) (*Store, error)`, `Store.{Create,List,Get,Update,Delete,Ping,Close}`, `NewServer(*Store) http.Handler`, `Book`, `ErrNotFound`.
