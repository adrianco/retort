# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `books.c:books_handle` |
| POST | /books | 201 book \| 400 | `books.c:write_book` |
| GET | /books[?author=] | 200 `[book]` | `books.c:list_books` |
| GET | /books/{id} | 200 book \| 404 | `books.c:get_one` |
| PUT | /books/{id} | 200 book \| 400 \| 404 | `books.c:write_book` |
| DELETE | /books/{id} | 204 \| 404 | `books.c:delete_book` |

All other paths/methods return 404 or 405 with a JSON `{"error": "..."}` body.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

- `int books_open(const char *path, sqlite3 **db)` — open DB and create schema.
- `response_t books_handle(sqlite3 *db, method, path, query, body)` — route+handle one request, returns `{int status, char *body}`.
