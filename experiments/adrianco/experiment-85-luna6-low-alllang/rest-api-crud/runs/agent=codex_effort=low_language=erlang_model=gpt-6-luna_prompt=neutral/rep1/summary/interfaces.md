# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status:ok}` | `books_api_handler:route/3` |
| POST | /books | `201 Book` / `400 {error}` | `books_api_handler:route/3` |
| GET | /books | `200 [Book]` (optional `?author=`) | `books_api_handler:route/3` |
| GET | /books/{id} | `200 Book` / `404` | `books_api_handler:route/3` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `books_api_handler:route/3` |
| DELETE | /books/{id} | `204` / `404` | `books_api_handler:route/3` |

All routes dispatch to a single `books_api_handler` (Cowboy `init/2`), which pattern-matches
method + `path_info` in `route/3`. Responses are JSON (`jsx:encode`) with `content-type: application/json`.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL,
`year` INTEGER, `isbn` TEXT.

## Library API

`books_api_store` gen_server: `create/1`, `list/1`, `get/1`, `update/2`, `delete/1` — each a
`gen_server:call`. Persistence is implemented by spawning the external `sqlite3 -json` executable
per query and decoding its JSON output.
