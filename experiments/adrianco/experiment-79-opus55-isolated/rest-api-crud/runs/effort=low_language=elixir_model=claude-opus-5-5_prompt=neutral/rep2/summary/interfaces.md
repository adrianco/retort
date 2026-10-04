# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | 200 `{"status":"ok"}` | `router.ex` get "/health" |
| POST | /books | 201 `Book` / 422 / 400 | `router.ex` post "/books" |
| GET | /books | 200 `[Book]` (optional `?author=` exact, case-insensitive) | `router.ex` get "/books" |
| GET | /books/:id | 200 `Book` / 404 | `router.ex` get "/books/:id" |
| PUT | /books/:id | 200 `Book` / 404 / 422 | `router.ex` put "/books/:id" |
| DELETE | /books/:id | 204 (empty) / 404 | `router.ex` delete "/books/:id" |
| (any) | * | 404 `{"error":"not found"}` | `router.ex` match _ |

Error codes: 400 (malformed JSON / non-object body), 404 (unknown book or route),
415 (unsupported media type), 422 (validation failure with `details` map).

## Library API

- `BookApi.Store` — `list/1`, `get/1`, `create/1`, `update/2`, `delete/1`, `delete_all/0`
- `BookApi.Book.validate/1` — `{:ok, attrs}` | `{:error, errors_map}`

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL),
`author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
