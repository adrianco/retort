# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `api.c:api_handle` |
| POST | /books | 201 `Book` \| 400 | `api.c:save_book` |
| GET | /books | 200 `[Book]` (`?author=` exact filter) | `api.c:list_books` |
| GET | /books/{id} | 200 `Book` \| 404 | `api.c:get_book` |
| PUT | /books/{id} | 200 `Book` \| 400 \| 404 | `api.c:save_book` |
| DELETE | /books/{id} | 204 \| 404 | `api.c:delete_book` |

Unsupported methods on a known path return 405; unknown routes return 404;
bodies over 1 MB return 413. All non-empty bodies are `application/json`; errors
are `{"error":"..."}`.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL,
`author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## Library API

- `int api_handle(sqlite3 *db, method, path, query, body, char **out)` — routes one
  request, returns the HTTP status, writes a malloc'd JSON body to `*out`.
- `sqlite3 *api_open_db(const char *path)` — opens and migrates the DB (`:memory:` supported).
