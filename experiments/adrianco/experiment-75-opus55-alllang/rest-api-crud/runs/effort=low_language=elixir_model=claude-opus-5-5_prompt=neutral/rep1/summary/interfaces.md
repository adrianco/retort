# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: "ok"}` | `router.ex:9` |
| GET | /books | `200 [Book]` (optional `?author=` exact-match filter) | `router.ex:11` |
| POST | /books | `201 Book` \| `422 {errors}` | `router.ex:16` |
| GET | /books/:id | `200 Book` \| `404` | `router.ex:25` |
| PUT | /books/:id | `200 Book` \| `404` \| `422 {errors}` | `router.ex:33` |
| DELETE | /books/:id | `204` \| `404` | `router.ex:45` |
| (any other) | * | `404 {error: "not found"}` | `router.ex:53` |

## Data schema

`books` table (SQLite, `repo.ex:22`): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Library API

`Books.Repo` GenServer: `list/1` (optional author filter), `get/1`, `create/1`, `update/2`, `delete/1`, `reset/0` (test helper). Validation lives in `Books.Router.validate/1` — requires non-blank `title` and `author`, type-checks `year` (integer) and `isbn` (string).
