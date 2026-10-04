# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `app.c:app_handle` |
| POST | /books | 201 created book / 400 | `app.c:create_book` |
| GET | /books | 200 `[Book]`; `?author=` exact filter | `app.c:list_books` |
| GET | /books/{id} | 200 book / 404 | `app.c:get_book` |
| PUT | /books/{id} | 200 updated book / 400 / 404 | `app.c:update_book` |
| DELETE | /books/{id} | 204 no body / 404 | `app.c:delete_book` |

Unknown paths return 404; unsupported methods on a known path return 405.
All responses are `Content-Type: application/json` (except 204). Errors are
`{"error": "<message>"}`.

## Library API (app.h)

- `sqlite3 *app_open_db(const char *path)` — open/create DB and ensure schema (`:memory:` supported).
- `response_t app_handle(sqlite3 *db, const char *method, const char *target, const char *body)` — route one request; caller frees `response_t.body`.

## Data schema

`books` table: `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
Index `books_author` on `author`.

## Configuration (env vars)

- `PORT` (default 8080)
- `DB_PATH` (default `books.db`)
