# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `books.c:books_handle` |
| POST | /books | 201 `Book` / 400 | `books.c:create_book` |
| GET | /books | 200 `[Book]` | `books.c:list_books` |
| GET | /books?author=Name | 200 `[Book]` (exact author) | `books.c:list_books` |
| GET | /books/{id} | 200 `Book` / 404 | `books.c:get_book` |
| PUT | /books/{id} | 200 `Book` / 400 / 404 | `books.c:update_book` |
| DELETE | /books/{id} | 204 / 404 | `books.c:delete_book` |

Unmatched paths return 404; unsupported methods on a known path return 405.
Errors are JSON `{"error":"..."}`.

## Library API

- `int books_init_db(sqlite3 *db)` — create the `books` table if absent.
- `response_t books_handle(sqlite3 *db, const char *method, const char *path, const char *body)` — pure request→response function; `path` may carry a query string. Caller frees `response_t.body`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
