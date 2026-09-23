# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {status: "ok"}` | `router.ex:8` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `router.ex:10` |
| POST | /books | `201 Book` \| `422 {errors}` | `router.ex:15` |
| GET | /books/:id | `200 Book` \| `404` | `router.ex:23` |
| PUT | /books/:id | `200 Book` \| `422 {errors}` \| `404` | `router.ex:31` |
| DELETE | /books/:id | `204` \| `404` | `router.ex:43` |
| (any) | * | `404 {error: "not found"}` | `router.ex:51` |

## Data schema

`books` table (SQLite via Exqlite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER), `isbn` (TEXT).

## Library API

`Books.Repo` GenServer: `list/1` (optional author), `get/1`, `create/1`, `update/2`, `delete/1`, `reset/0` (test support).
