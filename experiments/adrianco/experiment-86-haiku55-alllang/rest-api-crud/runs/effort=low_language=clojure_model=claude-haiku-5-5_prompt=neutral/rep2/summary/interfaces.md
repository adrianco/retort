# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201 Book` / `400` / `422` | `handler.clj:handle-create` |
| GET | /books | `200 [Book]` (optional `?author=`) | `handler.clj:handle-list` |
| GET | /books/{id} | `200 Book` / `404` | `handler.clj:handle-get` |
| PUT | /books/{id} | `200 Book` / `400` / `422` / `404` | `handler.clj:handle-update` |
| DELETE | /books/{id} | `204` / `404` | `handler.clj:handle-delete` |
| GET | /health | `200 {"status":"ok"}` | `handler.clj:handle-health` |

Status codes: `400` malformed/non-object body, `404` route or book not found, `405` method not allowed, `422` validation failure (per-field messages under `fields`), `500` unexpected error.

## Data schema

`books` table (SQLite): `id` (INTEGER PK AUTOINCREMENT), `title` (TEXT NOT NULL), `author` (TEXT NOT NULL), `year` (INTEGER, nullable), `isbn` (TEXT, nullable).

## Library API

- `db/make-datasource` returns a next.jdbc datasource and bootstraps the schema.
- `validation/validate-book` → nil when valid, else `{field → message}`.
- `validation/normalize-book` trims strings, keeps only known keys.
