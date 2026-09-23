# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: "ok"}` | `router.ex:get "/health"` |
| POST | /books | `201 Book` / `422 {errors}` / `400 invalid JSON` | `router.ex:post "/books"` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `router.ex:get "/books"` |
| GET | /books/:id | `200 Book` / `404` | `router.ex:get "/books/:id"` |
| PUT | /books/:id | `200 Book` / `404` / `422 {errors}` | `router.ex:put "/books/:id"` |
| DELETE | /books/:id | `204` / `404` | `router.ex:delete "/books/:id"` |
| (any) | * | `404 {error: "not found"}` | `router.ex:match _` |

## Data schema

`books` table (SQLite, exqlite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Library API

`Books.Repo`: `list/1`, `get/1`, `create/1`, `update/2`, `delete/1`, `reset/0` (GenServer wrapping one SQLite connection). `Books.Validator.validate/1` → `{:ok, attrs}` | `{:error, errors_map}`.
