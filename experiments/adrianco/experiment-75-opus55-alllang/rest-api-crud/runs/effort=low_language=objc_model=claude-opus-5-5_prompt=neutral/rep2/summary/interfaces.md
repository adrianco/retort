# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `BookAPI.m:handleMethod` |
| POST | /books | `201 Book` / `400` | `BookAPI.m:handleMethod` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter) | `BookAPI.m:handleMethod` |
| GET | /books/{id} | `200 Book` / `400` / `404` | `BookAPI.m:handleMethod` |
| PUT | /books/{id} | `200 Book` / `400` / `404` | `BookAPI.m:handleMethod` |
| DELETE | /books/{id} | `204` / `404` | `BookAPI.m:handleMethod` |

Unsupported methods on a known path return `405`. Unknown paths return `404`.

## Library API

`BookAPI.handleMethod:target:body:` is transport-independent — tests call it directly without the socket layer. `BookStore` exposes the five CRUD primitives listed in modules.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).
