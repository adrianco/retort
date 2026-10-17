# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: ok}` / `503 {status: unavailable}` | `server.py:_health` |
| GET | /books | `200 [Book]` (supports `?author=` exact, case-insensitive) | `server.py:_list_books` |
| POST | /books | `201 Book` + `Location` header / `400` | `server.py:_create_book` |
| GET | /books/{id} | `200 Book` / `404` | `server.py:_get_book` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `server.py:_update_book` |
| DELETE | /books/{id} | `204` / `404` | `server.py:_delete_book` |

Other mapped responses: `404 {error}` for unknown routes, `405 {error}` + `Allow` header for wrong methods, `413` for oversized bodies, `400` for malformed/non-object JSON, `500` for unexpected errors.

## CLI commands

`python -m book_api [--host H] [--port P] [--db FILE] [--log-level LVL]` — starts the threaded HTTP server.

## Library API

Exported from `book_api`: `create_server(repository, host, port)`, `BookRepository(database)`, `BookHTTPServer`, `Book`, `BookFields`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT). Index `idx_books_author` on `author COLLATE NOCASE`.
