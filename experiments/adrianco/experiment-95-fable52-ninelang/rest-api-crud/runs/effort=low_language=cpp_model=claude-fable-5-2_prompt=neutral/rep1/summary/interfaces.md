# Interfaces

## HTTP routes

| Method | Path | Returns | Handler |
|--------|------|---------|---------|
| GET | /health | `200 {"status":"ok"}` | `app.cpp:route` |
| GET | /books | `200 [Book]` (optional `?author=` filter) | `app.cpp:route` |
| POST | /books | `201 Book` \| `400 {error}` | `app.cpp:route` → `store.create` |
| GET | /books/{id} | `200 Book` \| `404 {error}` | `app.cpp:route` → `store.get` |
| PUT | /books/{id} | `200 Book` \| `400` \| `404` | `app.cpp:route` → `store.update` |
| DELETE | /books/{id} | `204` \| `404 {error}` | `app.cpp:route` → `store.remove` |

Unsupported methods on known paths return `405`; unknown paths return `404`.

## Data schema

`books` table (SQLite): `id` INTEGER PK AUTOINCREMENT, `title` TEXT NOT NULL,
`author` TEXT NOT NULL, `year` INTEGER NULL, `isbn` TEXT NULL. Index
`idx_books_author` on `author`.

## Library API

- `BookStore(path)` — opens/creates SQLite DB; `create/list/get/update/remove`, mutex-guarded.
- `handleRequest(store, Request) -> Response` — pure routing entry, exception-safe (500 on throw).
- `json::parse(text) -> optional<Value>`, `json::quote(s)` — embedded JSON support.
