# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `router.ex:2` |
| POST | /books | `201 Book` / `400` invalid JSON / `422` missing title/author | `router.ex:4` |
| GET | /books | `200 [Book]`, optional `?author=` filter | `router.ex:13` |
| GET | /books/{id} | `200 Book` / `404` | `router.ex:16` |
| PUT | /books/{id} | `200 Book` / `400` / `422` / `404` | `router.ex:24` |
| DELETE | /books/{id} | `204` / `404` | `router.ex:37` |
| (any other) | * | `404 {"error":"Not found"}` | `router.ex:49` |

## Data schema

`books` table (SQLite, created in `store.ex:13`):
id (INTEGER PK AUTOINCREMENT), title (TEXT NOT NULL), author (TEXT NOT NULL), year (INTEGER), isbn (TEXT).

## Library API

- `BookApi.Router.dispatch(method, path, body, query)` → `{status, json_body}`
- `BookApi.JSON.encode/1`, `BookApi.JSON.decode/1`
- `BookApi.Store.{create/1, list/1, get/1, update/2, delete/1}`
