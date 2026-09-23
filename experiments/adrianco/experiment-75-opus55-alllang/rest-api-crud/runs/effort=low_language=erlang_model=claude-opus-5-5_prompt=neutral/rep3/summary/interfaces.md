# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `books_api.erl:route/4` |
| POST | /books | 201 book \| 400 | `books_api.erl:route/4` → `books_db:create/1` |
| GET | /books[?author=] | 200 `[book]` | `books_api.erl:route/4` → `books_db:list/1` |
| GET | /books/{id} | 200 book \| 404 | `books_api.erl:book_route/3` → `books_db:get/1` |
| PUT | /books/{id} | 200 book \| 400 \| 404 | `books_api.erl:book_route/3` → `books_db:update/2` |
| DELETE | /books/{id} | 204 \| 404 | `books_api.erl:book_route/3` → `books_db:delete/1` |

Unmatched method on a known path returns 405; unknown paths return 404; handler exceptions are caught and return 500 (`books_http.erl:safe_handle/3`).

## Data schema

DETS table `books_table` (type `set`), key = integer `id`, value = book map with keys
`<<"id">>`, `<<"title">>`, `<<"author">>`, `<<"year">>` (int|null), `<<"isbn">>` (str|null).
Next id derived by scanning existing keys at init (`books_db.erl:init/1`).

## Library API

- `books_api:validate/1` — validates a decoded JSON map, returns `{ok, Book} | {error, [Msg]}`.
- `books_db` gen_server client functions: `create/1`, `list/1`, `get/1`, `update/2`, `delete/1`.
