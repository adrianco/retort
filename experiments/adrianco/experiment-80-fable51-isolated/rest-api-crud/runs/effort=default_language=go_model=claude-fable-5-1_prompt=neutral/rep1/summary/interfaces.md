# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status}` \| 503 | `handlers.go:health` |
| POST | /books | `201 Book` \| 400 | `handlers.go:createBook` |
| GET | /books | `200 [Book]` (`?author=` filter) | `handlers.go:listBooks` |
| GET | /books/{id} | `200 Book` \| 400 \| 404 | `handlers.go:getBook` |
| PUT | /books/{id} | `200 Book` \| 400 \| 404 | `handlers.go:updateBook` |
| DELETE | /books/{id} | `204` \| 400 \| 404 | `handlers.go:deleteBook` |

Unmatched routes/methods return JSON `{"error": ...}` with 404/405 via a mux wrapper.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER DEFAULT 0), `isbn` (TEXT DEFAULT '').

## Library API

`NewStore(dsn) -> *Store` with `Create/List/Get/Update/Delete/Ping/Close`; `NewHandler(*Store) -> http.Handler`.
