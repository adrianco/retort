# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `books.c:books_handle` |
| POST | /books | `201 Book \| 400` | `books.c:save_book` (id=0) |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `books.c:list_books` |
| GET | /books/{id} | `200 Book \| 404` | `books.c:get_book` |
| PUT | /books/{id} | `200 Book \| 400 \| 404` | `books.c:save_book` (id>0) |
| DELETE | /books/{id} | `204 \| 404` | `books.c:delete_book` |

Unsupported methods on a known path return `405`. Content-Type is
`application/json`; errors return `{"error":"..."}`.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API (books.h)

- `int books_init_db(sqlite3 *db)` — create table if absent.
- `response_t books_handle(sqlite3 *db, const char *method, const char *path, const char *body)` —
  route one request; transport-independent so tests call it directly.
