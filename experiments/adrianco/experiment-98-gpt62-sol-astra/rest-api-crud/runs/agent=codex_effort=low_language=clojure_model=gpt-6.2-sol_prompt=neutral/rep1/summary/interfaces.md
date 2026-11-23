# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| POST | /books | `201 Book` + `Location` header, or `400` | `core.clj:collection-route` → `db/create!` |
| GET | /books | `200 [Book]` (optional `?author=` exact filter), or `400` | `core.clj:collection-route` → `db/list-books` |
| GET | /books/{id} | `200 Book` or `404` | `core.clj:book-route` → `db/get-book` |
| PUT | /books/{id} | `200 Book` (full replace), `400`, or `404` | `core.clj:book-route` → `db/update!` |
| DELETE | /books/{id} | `204` (empty) or `404` | `core.clj:book-route` → `db/delete!` |
| GET | /health | `200 {"status":"ok"}` | `core.clj:make-app` inline |

Unmatched method on `/books` → `405` with `Allow` header; unmatched method on `/books/{id}` → `405`; unknown URI → `404`. Uncaught `SQLException` → `500 {"error":"Database error"}`.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL, `author` TEXT NOT NULL, `year` INTEGER (nullable), `isbn` TEXT (nullable).

## Validation

`title` and `author` must be nonblank strings; `year` (if present) must be an integer; `isbn` (if present) must be a string. Malformed JSON → `400 {"error":"Malformed JSON"}`.
