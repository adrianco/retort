# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `router.ex:17` |
| POST | /books | `201 Book` / `422 errors` | `router.ex:21` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `router.ex:28` |
| GET | /books/{id} | `200 Book` / `404` | `router.ex:35` |
| PUT | /books/{id} | `200 Book` / `404` / `422 errors` | `router.ex:44` |
| DELETE | /books/{id} | `204` / `404` | `router.ex:55` |
| (any) | unmatched | `404 {"error":"not found"}` | `router.ex:64` |

Malformed JSON bodies surface as `400` via `Plug.Parsers`.

## Data schema

`books` table (`repo.ex:40`): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL,
`author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## Library API

`BooksApi.Book`: `create/1`, `list/1`, `get/1`, `update/2`, `delete/1`, `validate/1`
returning `{:ok, _}` / `{:error, :not_found}` / `{:error, errors_map}`.
`BooksApi.Repo.query/3` runs parameterized SQL through a GenServer-owned connection.
